import glob, struct, zlib, sys

def read_png(path):
    with open(path, 'rb') as f:
        data = f.read()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    pos = 8
    width = height = None
    idat = b''
    while pos < len(data):
        ln = struct.unpack('>I', data[pos:pos+4])[0]
        typ = data[pos+4:pos+8]
        chunk = data[pos+8:pos+8+ln]
        if typ == b'IHDR':
            width, height, bd, ct = struct.unpack('>IIBB', chunk[:10])
        elif typ == b'IDAT':
            idat += chunk
        pos += 12 + ln
    raw = zlib.decompress(idat)
    # assume 8-bit RGBA or RGB
    bpp = 4 if ct == 6 else 3
    stride = width * bpp + 1
    rows = []
    prev = bytearray(width * bpp)
    out = []
    for y in range(height):
        line = raw[y*stride:(y+1)*stride]
        filt = line[0]
        cur = bytearray(line[1:])
        if filt == 1:
            for i in range(bpp, len(cur)):
                cur[i] = (cur[i] + cur[i-bpp]) & 0xff
        elif filt == 2:
            for i in range(len(cur)):
                cur[i] = (cur[i] + prev[i]) & 0xff
        elif filt == 3:
            for i in range(len(cur)):
                a = cur[i-bpp] if i >= bpp else 0
                cur[i] = (cur[i] + ((a + prev[i]) >> 1)) & 0xff
        elif filt == 4:
            for i in range(len(cur)):
                a = cur[i-bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i-bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p-a), abs(p-b), abs(p-c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                cur[i] = (cur[i] + pr) & 0xff
        out.append(bytes(cur))
        prev = cur
    return width, height, bpp, out

for path in sorted(glob.glob(sys.argv[1] + '/*.png')):
    w, h, bpp, rows = read_png(path)
    # find magenta-ish pixels (r>200,g<80,b>200)
    xs = []
    for y in range(0, h, 4):
        row = rows[y]
        for x in range(w):
            r, g, b = row[x*bpp], row[x*bpp+1], row[x*bpp+2]
            if r > 180 and g < 100 and b > 180:
                xs.append(x)
    if xs:
        print(f"{path}: {w}x{h} magenta x range {min(xs)}..{max(xs)} (count {len(xs)})")
    else:
        print(f"{path}: {w}x{h} NO magenta found")
