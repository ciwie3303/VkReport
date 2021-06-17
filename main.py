import json
import random
import asyncio
import config
import core.api as api
import core.logger as log
import core.loop as loop

users = list()


class HardbassTusovka(Exception):
    pass


def accounts_read():
    with open('accounts.txt', 'r') as f:
        res = f.readlines()

    for i in range(len(res)):
        res[i] = res[i].replace('\n', '').replace('\r', '').split(':')
        if len(res[i]) != 2:
            raise HardbassTusovka('Неверная структура accounts.txt, строка {}.'.format(i + 1))

    return res


def db_read():
    with open('db.json', 'r') as f:
        res = f.read()
    return json.loads(res)


def db_write(data):
    with open('db.json', 'w+') as f:
        f.write(json.dumps(data))


def proxy_read():
    with open('proxy.txt', 'r') as f:
        res = f.readlines()

    for i in range(len(res)):
        s = res[i].replace('\n', '').replace('\r', '')
        res[i] = {'https': s}

    return res


def main():

    if config.use_proxy:
        proxy_list = False
        try:
            proxy_list = proxy_read()
        except FileNotFoundError:
            return log.error('proxy.txt не найден или не содержит адресов, однако use_proxy выставлен как True.')

    db = False
    try:
        db = db_read()
    except FileNotFoundError:
        log.info('Кешированных авторизованных пользователей не обнаружено.')
    except ValueError:
        log.warning('db.json содержит невалидный JSON. Содержимое файла будет перезаписано.')

    users.extend(db if db else [])

    if len(users):
        log.info('Проверяю токены из db.json')
        for user in users:
            if config.use_proxy:
                user['proxy'] = proxy_list[random.randint(0, len(proxy_list) - 1)]

            if not api.check_token(user):
                if config.full_version:
                    log.info('Сессия пользователя {} невалидна, пробую переавторизоваться.'.format(user['login']))
                else:
                    log.info('Токен пользователя {} невалиден, пробую переавторизоваться.'.format(user['login']))
                new_user = api.auth(user)
                if not new_user:
                    log.error('Не удалось авторизовать аккаунт {}.'.format(user['login']))
                    users.remove(user)
                else:
                    log.info('Аккаунт {} успешно авторизован.'.format(user['login']))
                    users[users.index(user)] = new_user

    accounts = False
    try:
        accounts = accounts_read()
    except FileNotFoundError:
        if len(users):
            log.info('Авторизационных данных не обнаружено, использую кеш из db.json')
        else:
            return log.error('Авторизационные данные и кеш не обнаружены. Отсутствуют аккаунты.')
    except HardbassTusovka as e:
        log.error(e)

    if accounts:
        log.info('Авторизую новых пользователей из accounts.txt')
        for acc in accounts:
            if any(d.get('login', None) == acc[0] for d in users):
                continue

            user = {'login': acc[0], 'password': acc[1]}

            if config.use_proxy:
                user['proxy'] = proxy_list[random.randint(0, len(proxy_list) - 1)]

            user = api.auth(user)

            if not user:
                log.error('Не удалось авторизовать аккаунт {}.'.format(acc[0]))
            else:
                log.info('Аккаунт {} успешно авторизован.'.format(acc[0]))
                users.append(user)

    if len(users):
        db_write(users)
        log.info('Кеш пользователей сохранен.')
        log.info('Авторизовано {} аккаунтов.'.format(len(users)))
    else:
        return log.error('По результатам авторизации не обнаружено ни одного валидного аккаунта')

    asyncio.run(loop.loop(users))


if __name__ == '__main__':
    main()