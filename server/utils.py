def fnv32a(msg):
    hval = 0x811c9dc5
    fnv_32_prime = 0x01000193
    uint32_max = 2 ** 32
    for s in msg:
        hval = hval ^ ord(s)
        hval = (hval * fnv_32_prime) % uint32_max
    return hval
