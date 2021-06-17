import asyncio
import random
import requests
import json
import config
import re
import core.logger as log

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.72 Safari/537.36 Edg/90.0.818.42'
}

report_endpoint = 'https://api.vk.com/method/wall.reportComment?owner_id={}&comment_id={}&reason={}&access_token={}&v=5.103'
auth_endpoint = 'https://oauth.vk.com/token?client_id=2274003&client_secret=hHbZxrka2uZ6jB1inYsH&grant_type=password&username={}&password={}&scope=nohttps.all'
check_endpoint = 'https://api.vk.com/method/users.get?&access_token={}&v=5.103'
auth_full_endpoint = 'https://login.vk.com/?act=login&role=pda&_origin=https://m.vk.com&ip_h={}&lg_h={}&email={}&pass={}'
comment_page_endpoint = 'https://vk.com/wall{}_{}?reply={}'
report_hash_endpoint = 'https://vk.com/al_wall.php?act=spam&al=1&from=&hash={}&post={}_{}'
report_full_endpoint = 'https://vk.com/reports.php?act=new_report&al=1&hash={}&item_id={}&oid={}&reason={}&type=wall'


def auth(user):
    try:
        resp = requests.get(auth_endpoint.format(user['login'], user['password']), headers=headers,
                            proxies=user['proxy'] if config.use_proxy else None).text
    except (requests.exceptions.ProxyError, requests.exceptions.ConnectionError) as e:
        log.error('Прокся {} сдохла.'.format(user['proxy']))
        return False

    try:
        data = json.loads(resp)
        user.update({'access_token': data['access_token'], 'id': data['user_id']})
        if config.full_version:
            user = auth_full(user)
        return user
    except:
        return False


def auth_full(user):
    r = requests.session()
    loginpage = r.get('https://vk.com', headers=headers, proxies=user['proxy'] if config.use_proxy else None).text
    try:
        ip_h = re.search(r'<input type="hidden" name="ip_h" value="([a-f0-9]+)"', loginpage).group(1)
        lg_h = re.search(r'<input type="hidden" name="lg_h" value="([a-f0-9]+)"', loginpage).group(1)
    except AttributeError:
        return False

    r.get(auth_full_endpoint.format(ip_h, lg_h, user['login'], user['password']),
          headers=headers, proxies=user['proxy'] if config.use_proxy else None)

    cookie_dict = r.cookies.get_dict()

    if 'remixsid' not in cookie_dict:
        return False
    else:
        user.update({'cookies': cookie_dict})
        return user


def check_token(user):
    if config.full_version:
        return check_session(user)

    try:
        resp = requests.get(check_endpoint.format(user['access_token']), headers=headers,
                            proxies=user['proxy'] if config.use_proxy else None).text
    except (requests.exceptions.ProxyError, requests.exceptions.ConnectionError) as e:
        log.error('Прокся {} сдохла.'.format(user['proxy']))
        return False

    return True if 'error' not in resp else False


def check_session(user):
    if 'cookies' not in user:
        return False

    try:
        check = requests.get('https://vk.com/dev', allow_redirects=False, cookies=user['cookies'], headers=headers,
                             proxies=user['proxy'] if config.use_proxy else None).text
    except (requests.exceptions.ProxyError, requests.exceptions.ConnectionError) as e:
        log.error('Прокся {} сдохла.'.format(user['proxy']))
        return False

    try:
        id = re.search(r'id: ([0-9]+),', check).group(1)
    except AttributeError:
        return False

    return True


async def report(target, user, reason=3):
    delay = random.randint(1, config.max_delay)
    await asyncio.sleep(delay)

    if config.full_version:
        state = await report_full(target, user)
        if not state:
            return log.error('Неизвестная ошибка при отправке репорта от имени пользователя {}.'.format(user['login']))
        else:
            return log.info('Репорт от имени пользователя {} успешно отправлен'.format(user['login']))

    try:
        resp = requests.get(report_endpoint.format(target[0], target[2], reason, user['access_token']),
                            headers=headers, proxies=user['proxy'] if config.use_proxy else None).text
    except (requests.exceptions.ProxyError, requests.exceptions.ConnectionError) as e:
        log.error('Прокся {} сдохла.'.format(user['proxy']))

    if 'error' in resp:
        log.error('Неизвестная ошибка при отправке репорта от имени пользователя {}.'.format(user['login']))
    elif 'response' in resp:
        log.info('Репорт от имени пользователя {} успешно отправлен'.format(user['login']))


async def report_full(target, user, reason=3):
    first_hash_page = requests.get(comment_page_endpoint.format(target[0], target[1], target[2]),
                                   cookies=user['cookies'], headers=headers,
                                   proxies=user['proxy'] if config.use_proxy else None).text

    pattern = "wall\.markAsSpam\(this, '{}_{}', '([0-9a-f]+)'\)".format(target[0], target[2])
    try:
        first_hash = re.search(pattern, first_hash_page).group(1)
    except AttributeError:
        return False

    second_hash_page = requests.get(report_hash_endpoint.format(first_hash, target[0], target[2]),
                                    cookies=user['cookies'], headers=headers,
                                    proxies=user['proxy'] if config.use_proxy else None).text

    pattern2 = "window\.showReportReasonDescriptionPopup\('wall', '{}', {}, {}, '([0-9a-f]+)'".format(target[0],
                                                                                                      target[2], reason)
    try:
        second_hash = re.search(pattern2, second_hash_page).group(1)
    except AttributeError:
        return False

    resp = requests.get(report_full_endpoint.format(second_hash, target[2], target[0], reason),
                        cookies=user['cookies'], headers=headers,
                        proxies=user['proxy'] if config.use_proxy else None).text

    return True
