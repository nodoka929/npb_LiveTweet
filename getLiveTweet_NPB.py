from urllib.request import urlopen
import tweepy
from datetime import timedelta
import time
import sqlite3
from contextlib import closing
import datetime
from bs4 import BeautifulSoup
import urllib.request as req



# 対戦カードを取得
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
        # print(p)
        urls = p.get('href')
        # print(urls)
        p_ = p.select('.st-03')
        #print(p_)
        for p__ in p_:
            if '中止' in str(p__.text) or 'ノーゲーム' in str(p__.text):
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
    # 研究共通
    teamId_dic = {'巨人': 0, '中日': 1, '広島': 2, 'ヤクルト': 3, '阪神': 4, 'ＤｅＮＡ': 5,
                  '日本ハム': 6, 'ソフトバンク': 7, '楽天': 8, '西武': 9, 'ロッテ': 10, 'オリックス': 11}
    i = 0
    for p in q:
        print(p.text)
        if flag_list[i] == 1:
            teamId_list.append(teamId_dic[p.text])
        i += 1
    return gameId_list, teamId_list


#日付
def get_date(days_ago):
    date = datetime.date.today()
    date -= datetime.timedelta(days=days_ago)
    date_str = str(date)
    date_str = date_str[:4]+date_str[5:7]+date_str[8:10]
    return date_str


# 試合の開始時間と終了時間をスクレイピングで取得
def gametime(game_id):
    url = 'https://baseball.yahoo.co.jp/npb/game/' + game_id + '/top'
    print(url)
    res = req.urlopen(url)
    soup = BeautifulSoup(res, 'html.parser')
    time = []

    # 開始時間
    css_select = '#contentMain .bb-gameDescription time'
    q = soup.select(css_select)
    print(q[0].text)
    time.append(q[0].text[-5:-3])
    time.append(q[0].text[-2:])

    # 終了時間
    minutes = []
    css_select = '.bb-tableLeft .bb-tableLeft__data'
    q = soup.select(css_select)
    for q_ in q:
        # print(q_.text)
        if '時間' in q_.text:
            minutes = q_.text.split('時間')
    minutes[1] = minutes[1][:-1]
    print(minutes)

    time = time + minutes
    return time


# TwitterAPI
APIK = 'consumer_key'
APIS = 'consumer_secret'
AT = 'access_token'
AS = 'access_token_secret'
auth = tweepy.OAuthHandler(APIK, APIS)
auth.set_access_token(AT, AS)
api = tweepy.API(auth)


# TwitterAPI検索
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


# 時間指定 → クエリを作成 → ツイート検索関数（search_livetweet()）を実行
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
    tag_list = {0: '#kyojin OR #giants', 1: '#dragons OR #中日ドラゴンズ',\
            2: '#carp OR #広島カープ', 3: '#swallows OR #ヤクルトスワローズ',\
            4: '#hanshin OR #阪神タイガース', 5: '#baystars OR #ベイスターズ',\
            6: '#lovefighters OR #日ハム ', 7: '#sbhawks OR #ホークス',\
            8: '#rakuteneagles OR #楽天イーグルス', 9: '#seibulions OR #西武ライオンズ',\
            10: '#chibalotte OR #千葉ロッテマリーンズ', 11: '#bs2020 OR #バファローズ'}
    tag = tag_list[team_num]
    query = tag + ' exclude:retweets exclude:replies\
            since:' + date + '_' + sh + ':' + sm + ':00_JST \
            until:' + date + '_' + eh + ':' + em + ':59_JST lang:ja'
    search_livetweet(team_id, api, game_id, query)



# 例 --------------------------
n = 1
game_date = get_date(n) # 自動(n日前のデータを取得)
game_date = '20200401' # 手入力
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




