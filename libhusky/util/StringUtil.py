import subprocess


def tail(filename, n):
    p = subprocess.Popen(['tail', '-n', str(n), filename], stdout=subprocess.PIPE)
    soutput, sinput = p.communicate()
    return soutput.decode('utf-8')


def trim_string(string: str, limit: int, add_suffix: bool = True, trim_suffix: str = "\n\n..."):
    s = string

    if len(string) > limit:
        s = string[:limit]

        if add_suffix:
            s = s[:-len(trim_suffix)] + trim_suffix

    return s
