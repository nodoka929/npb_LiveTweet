
from urllib.request import urlopen
import tweepy
from datetime import timedelta
import time
import sqlite3
from contextlib import closing
import datetime
from bs4 import BeautifulSoup
import urllib.request as req




#ゲームID，チームID
def get_gameteamId(gamedate):
    url = 'https://sportsbull.jp/stats/npb/home/index/' + gamedate
    print(url)
    res = req.urlopen(url)
    soup = BeautifulSoup(res, 'html.parser')
    q = soup.select('.game-block a')
    gameId_list = []
    flag_list = [1 for i in range(12)]
    i = 0
    for p in q:
        urls = p.get('href')
        # 中止になったときの処理
        p_ = p.select('.st-03')
        for p__ in p_:
            if '中止' in str(p__.text):
                print('中止')
                flag_list[i] = 0
                flag_list[i+1] = 0
        if flag_list[i] == 1:
            print(urls[-10:])
            gameId_list.append(urls[-10:])
        i += 2
    print('flag_list: ',flag_list)
    q = soup.select('.game-block .play-box01 dt')
    teamId_list = []
    teamId_dict = {'巨人': 0, '中日': 1, '広島': 2, 'ヤクルト': 3, '阪神': 4, 'ＤｅＮＡ': 5,
                  '日本ハム': 6, 'ソフトバンク': 7, '楽天': 8, '西武': 9, 'ロッテ': 10, 'オリックス': 11}
    i = 0
    for p in q:
        if flag_list[i] == 1:
            teamId_list.append(teamId_dict[p.text])
        i += 1
    return gameId_list, teamId_list



# ============================================================================



# TwitterAPI
APIK = 'consumer_key'
APIS = 'consumer_secret'
AT = 'access_token'
AS = 'access_token_secret'
auth = tweepy.OAuthHandler(APIK, APIS)
auth.set_access_token(AT, AS)
api = tweepy.API(auth)

def search_livetweet(team_num, api, game_id, query):
    print(query)    # 最新のつぶやきから取得
    print('検索ページ：1')
    try:
        tweet_data = api.search(q=query, count=1)
    except tweepy.TweepError as e:
        print('エラー：15ふん待ちます')
        time.sleep(60 * 15)

    tweet_data = api.search(q=query, count=100)
    table_name = 'team' + str(team_num)
    # この関数はデータベースに保存する用
    saveDB_tweet(table_name, 0, tweet_data, game_id)
    print('************************************************\n')
    next_max_id = tweet_data[-1].id

    page = 1
    while True:
        page += 1
        print('検索ページ：' + str(page))
        try:
            tweet_data = api.search(q=query, count=100, max_id=next_max_id - 1)
            if len(tweet_data) == 0:
                break
            else:
                next_max_id = tweet_data[-1].id
                # この関数はデータベースに保存する用
                saveDB_tweet(table_name, page - 1, tweet_data, game_id)
        except tweepy.TweepError as e:
            print('エラー：15ふん待ちます')
            print(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
            print(e.reason)
            time.sleep(60 * 15)
            continue
        print('*'*40 + '\n')


# 試合の開始時間と終了時間をスクレイピングで取得
def gametime(game_id):
    url = 'https://baseball.yahoo.co.jp/npb/game/' + game_id + '/top'
    res = req.urlopen(url)
    soup = BeautifulSoup(res, 'html.parser')
    time = []

    # 開始時間
    css_select = '#gm_match .gamecard .column-center .stadium'
    q = soup.select(css_select)
    time.append(q[0].text[-6:-4])
    time.append(q[0].text[-3:-1])

    # 終了時間
    minutes = []
    while True:
        try:
            css_select = '#yjSNLiveDetaildata td'
            q = soup.select(css_select)
            minutes = q[1].text.split('時間')
            minutes[1] = minutes[1][:-1]
            break
        except:
            continue
    time = time + minutes
    return time


# 時間指定してツイート検索関数（search_livetweet()）を実行
def get_livetweet(team_id, game_id):
    date = game_id[:4] + '-' + game_id[4:6] + '-' + game_id[6:8]
    time = gametime(game_id)
    sh, sm = time[0], time[1]
    eh = int(time[0]) + int(time[2])
    em = int(time[1]) + int(time[3]) + 5  # 終了後5分
    if em >= 60:
        em -= 60
        eh += 1
    eh = '{0:02d}'.format(eh)
    em = '{0:02d}'.format(em)
    
    print(date, sh, sm, eh, em)
    tag_list = {0: '#kyojin OR #giants', 1: '#dragons', 2: '#carp', 3: '#swallows OR #yakultswallows',
                4: '#hanshin OR #tigers', 5: '#baystars', 6: '#lovefighters', 7: '#sbhawks',
                8: '#rakuteneagles', 9: '#seibulions', 10: '#chibalotte', 11: '#Orix_Buffaloes'}
    tag = tag_list[team_num]
    query = tag + ' exclude:retweets exclude:replies since:' + date + '_' + sh + ':' + sm + ':00_JST until:' + date + '_' + eh + ':' + em + ':59_JST lang:ja'
    search_livetweet(team_id, api, game_id, query)




# ============================================================================


# gameデータベースの gameId_list に gameIdを保存
def gameId_list_insert(game_id,team,awayhome):
    with closing(sqlite3.connect('/Users/nodokaf/myStudy_M/data/database/game.db')) as con:
        cur = con.cursor()
        sql_insert = 'insert into gameId_list(gameId,teamId,away_home) values(?,?,?)'
        value = [game_id,team,awayhome]
        cur.execute(sql_insert,value)
        con.commit()


#日付
#game_date = '20190504'
def get_date(days_ago):
	date = datetime.date.today()
	date -= datetime.timedelta(days=days_ago)
	date_str = str(date)
	date_str = date_str[:4]+date_str[5:7]+date_str[8:10]
	return date_str



# 例 --------------------------
n = 1
game_date = get_date(n) # 自動(n日前のデータを取得)
game_date = '20190919' # 手入力
print(game_date,'のデータを取得,')
# -----------------------------


#ゲームID，チームIDのリスト
gameteamId_list = get_gameteamId(game_date)
gameId_list = gameteamId_list[0]
teamId_list = gameteamId_list[1]
print('gameId_list:',gameId_list)
print('teamId_list:',teamId_list)

print('='*60 + '\n')

for i in range(len(gameId_list)):
    game_id = gameId_list[i]

    #away
    team_id = teamId_list[2*i+1]
    get_livetweet(team_id, game_id)
    print('='*60 + '\n')

    #home
    team_id = teamId_list[2*i]
    get_livetweet(team_id, game_id)
    print('='*60 + '\n')




