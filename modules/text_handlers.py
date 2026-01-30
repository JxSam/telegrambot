

def convert_markdown_to_html(markdown_text: str) -> str:
    """Конвертирует MarkdownV2 символы в HTML."""
    html_text = markdown_text

    # 1. Markdown в HTML
    html_text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', html_text)
    html_text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', html_text)
    html_text = re.sub(r'_(.+?)_', r'<i>\1</i>', html_text)
    html_text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', html_text)
    html_text = re.sub(r'~(.+?)~', r'<s>\1</s>', html_text)
    html_text = re.sub(r'`(.+?)`', r'<code>\1</code>', html_text)
    html_text = re.sub(r'```(?:\w+)?\n?(.+?)```', r'<pre>\1</pre>', html_text, flags=re.DOTALL)

    # 2. Очистка от одиночных/разорванных символов Markdown
    html_text = html_text.replace('*', '').replace('_', '').replace('~', '').replace('`', '')
    return html_text

def get_html_text(message) -> str:
    """Конвертирует объект Message из Telethon в HTML-разметку."""
    text = message.text
    if not text: return ""

    entities = message.entities if message.entities else []
    entities.sort(key=lambda x: x.offset)

    output = ""
    last_offset = 0

    for entity in entities:
        raw_text = text[last_offset:entity.offset]
        output += escape_html_entities(raw_text)

        entity_text = text[entity.offset:entity.offset + entity.length]

        if isinstance(entity, MessageEntityBold):
            output += f"<b>{entity_text}</b>"
        elif isinstance(entity, MessageEntityItalic):
            output += f"<i>{entity_text}</i>"
        elif isinstance(entity, MessageEntityStrike):
            output += f"<s>{entity_text}</s>"
        elif isinstance(entity, MessageEntityUnderline):
            output += f"<u>{entity_text}</u>"
        elif isinstance(entity, MessageEntitySpoiler):
            output += f"<tg-spoiler>{entity_text}</tg-spoiler>"
        elif isinstance(entity, MessageEntityCode):
            output += f"<code>{entity_text}</code>"
        elif isinstance(entity, MessageEntityPre):
            output += f"<pre>{entity_text}</pre>"
        elif isinstance(entity, MessageEntityTextUrl):
            output += f'<a href="{entity.url}">{entity_text}</a>'
        elif isinstance(entity, MessageEntityUrl):
            output += f'<a href="{entity_text}">{entity_text}</a>'
        elif isinstance(entity, MessageEntityMentionName):
            output += f'<a href="tg://user?id={entity.user_id}">{entity_text}</a>'
        elif isinstance(entity, MessageEntityCustomEmoji):
            output += f'<tg-emoji emoji-id="{entity.document_id}">{entity_text}</tg-emoji>'
        elif isinstance(entity, MessageEntityBlockquote):
            output += f"<blockquote>{entity_text}</blockquote>"
        else:
            output += escape_html_entities(entity_text)

        last_offset = entity.offset + entity.length

    remaining_text = text[last_offset:]
    output += escape_html_entities(remaining_text)

    # ФИНАЛЬНАЯ ЧИСТКА
    output = output.replace('&lt;', '<').replace('&gt;', '>').replace('&ast;', '').replace('&amp;ast;', '').replace(
        '&quot;', '"')
    return output

def escape_html_entities(text: str) -> str:
    """Экранирует специальные символы HTML: &, <, >."""
    return escape(text)