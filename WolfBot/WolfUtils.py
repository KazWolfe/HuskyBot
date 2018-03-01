def memberHasRole(member, role_id):
    for r in member.roles:
        if r.id == role_id:
            return True

    return False


def memberHasAnyRole(member, roles):
    if roles is None:
        return True

    for r in member.roles:
        if r.id in roles:
            return True

        return False


def getFancyGameData(member):
    fancy_game = ""
    if member.game is not None:
        state = {0: "Playing ", 1: "Streaming ", 2: "Listening to "}

        fancy_game += "("
        if member.game.url is not None:
            fancy_game += "["

        fancy_game += state[member.game.type]
        fancy_game += member.game.name

        if member.game.url is not None:
            fancy_game += "](" + member.game.url + ")"

        fancy_game += ")"

    return fancy_game


def tail(f, lines):
    total_lines_wanted = lines

    block_size = 1024
    f.seek(0, 2)
    block_end_byte = f.tell()
    lines_to_go = total_lines_wanted
    block_number = -1
    blocks = []  # blocks of size BLOCK_SIZE, in reverse order starting from the end of the file
    while lines_to_go > 0 and block_end_byte > 0:
        if block_end_byte - block_size > 0:
            # read the last block we haven't yet read
            f.seek(block_number * block_size, 2)
            blocks.append(f.read(block_size))
        else:
            # file too small, start from beginning
            f.seek(0, 0)
            # only read what was not read
            blocks.append(f.read(block_end_byte))
        lines_found = blocks[-1].count('\n')
        lines_to_go -= lines_found
        block_end_byte -= block_size
        block_number -= 1
    all_read_text = ''.join(reversed(blocks))
    return '\n'.join(all_read_text.splitlines()[-total_lines_wanted:])
