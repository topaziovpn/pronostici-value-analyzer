import urllib.request, json
data = json.loads(urllib.request.urlopen('https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard').read())
found = False
for ev in data['events']:
    odds = ev['competitions'][0].get('odds', [])
    if odds and isinstance(odds[0], dict) and 'provider' in odds[0]:
        print(odds[0]['provider']['name'])
        found = True
        break
if not found: print('No provider found')
