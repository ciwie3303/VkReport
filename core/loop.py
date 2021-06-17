import re
import asyncio
import config
import core.api as api
import core.logger as log


def get_url_from_file():
    with open(f'./commentbot/userdata/links.txt', 'r') as f:
        res = f.readlines()

    if len(res) == 0:
        return False
    ret = res[0].replace('\n', '').replace('\r', '')
    res.pop(0)

    with open(f'./commentbot/userdata/links.txt', 'w') as f:
        res = f.write(''.join(res))

    return ret


def get_target(target_url):
    target_re = re.search(
        r'https:\/\/vk.com\/[a-z0-9_.]+\?w=wall(\-?[0-9]+)_([0-9]+)_r([0-9]+)|https:\/\/.*?vk.com\/wall(\-?[0-9]+)_([0-9]+)\?reply=([0-9]+)',
        target_url)
    target = list(filter(None, list(target_re.groups()) if target_re is not None else []))

    if len(target) < 3:
        return False
    else:
        return target


async def loop(users):
    while True:
        if config.mode == 0:
            target_url = input('Вставьте ссылку на комментарий: ').replace(' ', '')
        elif config.mode == 1:
            target_url = get_url_from_file()
            if not target_url:
                await asyncio.sleep(config.file_delay)
                continue
        else:
            return log.error('Каво')
        target = get_target(target_url)
        if not target:
            log.error('Некорректная ссылка на комментарий.')
            continue

        log.info('Работаем по {}, выполнение займет от 1 до {} секунд.'.format(target, config.max_delay))
        futures = []
        for user in users:
            futures.append(asyncio.ensure_future(api.report(target, user)))
        await asyncio.wait(futures)

        if config.mode == 1:
            await asyncio.sleep(config.file_delay)
