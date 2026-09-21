"""Общий блок «жизнь в Люксембурге» для трёх генераторов страниц.

Человек, который считает свою будущую зарплату, чаще всего только что
переехал или собирается. Ему же нужен язык, тест на гражданство, место
для ребёнка и приёмка квартиры — всё это уже сделано и лежит по разным
адресам, о которых он не узнает. Раньше в подвале была строка из трёх
ссылок без объяснения; здесь — что это и кому нужно.

Блок один на три продукта, но вставляется в каждый свой шаблон: общего
пакета на три репозитория заводить не за что, а расходится он редко.
"""

LINKS = [
    ('https://luxtax.alftech.space/', 'Net pay calculator',
     'What is left of a Luxembourg salary after tax and social security, in every tax class, '
     'with the Form 100 declaration.'),
    ('https://luxflash.alftech.space/words/', 'Luxembourgish vocabulary',
     '2 404 words by topic and level, with German, French and an example — the language the '
     'Sproochentest asks for.'),
    ('https://vivre.alftech.space/questions/', 'Citizenship test questions',
     'All 367 practice questions for Vivre ensemble au Grand-Duché, with the answer and why.'),
    ('https://handover.alftech.space/', 'État des lieux',
     'Record the flat room by room before the keys change hands: photos, meters, keys, one '
     'bilingual PDF to sign.'),
    ('https://www.kidspace.id/luxembourg', 'Places for children',
     '2 100 crèches, schools, playgrounds and shops across the twelve cantons, with hours '
     'and addresses.'),
    ('https://razbor.alftech.space/', 'Decode an official letter',
     'What the letter from the commune or the tax office actually asks you to do. In Russian.'),
]

CSS = '''
  .lux {{ margin:34px 0 0; padding-top:20px; border-top:1px solid {line}; }}
  .lux h2 {{ font-size:17px; margin:0 0 4px; }}
  .lux > p {{ color:{soft}; font-size:14.5px; margin:0 0 14px; max-width:60ch; }}
  .lux ul {{ list-style:none; margin:0; padding:0; display:grid;
    grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:10px; }}
  .lux li {{ margin:0; }}
  .lux a {{ text-decoration:none; display:block; }}
  .lux b {{ display:block; font-size:15px; color:{accent}; }}
  .lux span {{ color:{soft}; font-size:13.5px; line-height:1.45; display:block; margin-top:2px; }}
'''


def html(current_host, intro=None):
    """Блок без ссылки на самого себя: страница не ссылается на свой же дом."""
    items = ''.join(
        f'<li><a href="{url}"><b>{name}</b><span>{about}</span></a></li>'
        for url, name, about in LINKS if current_host not in url)
    text = intro or ('Everything else here for somebody who has just moved to Luxembourg. '
                     'All free, none of it asks for an account.')
    return (f'<section class="lux"><h2>Living in Luxembourg</h2>'
            f'<p>{text}</p><ul>{items}</ul></section>')


def css(line='#e3e8ef', soft='#5b6779', accent='#1b57a8'):
    return CSS.format(line=line, soft=soft, accent=accent)
