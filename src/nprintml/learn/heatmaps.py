import matplotlib.patches as patches
import matplotlib.pyplot as plt
from matplotlib.pyplot import cm
import numpy as np
import pickle

def numRows(hdr):
    """Calculate the number of rows needed for a given header's heatmap."""
    totalsize = 0
    for field in hdr.fields:
        totalsize += field['size']

    # Heatmap rows are 32 bits wide
    quotient, rem = divmod(totalsize, 32)
    if rem > 0:
        quotient += 1
    return quotient


def setArray(hdr):
    """Build 2D array filled with header values."""
    fullarray = []
    for field in hdr.fields:
        fullarray.append(field['vals'])
    hdr.arr = np.concatenate(fullarray)
    hdr.arr = np.reshape(hdr.arr, (numRows(hdr), 32))


def getHeatmap(hdr, outname, size=(5, 5)):
    """
    Generates a heatmap for a given packet header.

        Parameters:
                hdr (class): A header object
                outname (str): The name for an output file (e.g., "tcp_header_heatmap.pdf")
                size (tuple): The size of the matplotlib figure, defaults to (5,5)
    """
    fig = plt.figure(figsize=size)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)

    extent = [0, 32, numRows(hdr), 0]
    im = ax.imshow(hdr.arr, extent=extent, cmap=cm.plasma)
    hdr.color_matrix = im.cmap(im.norm(im.get_array()))

    rows = numRows(hdr)
    currentrow = rows
    position = 0
    for field in hdr.fields:
        rowcount = 1
        quotient = 0
        rem = 0
        if field['size'] > 32:
            quotient, rem = divmod(field['size'], 32)
            rowcount = quotient

        if field['size'] > 32:
            field['size'] = 32

        if position + field['size'] > 32 and position + rem == 32:
            tmp = rem
            rem = field['size']
            field['size'] = tmp

        fc = 'none'
        if field['name'] == '':
            fc = 'w'
        rectangle = plt.Rectangle(
            (position, (currentrow - rows)), field['size'], rowcount, edgecolor='k', fc=fc)
        plt.gca().add_patch(rectangle)

        rx, ry = rectangle.get_xy()
        cx = rx + rectangle.get_width()/2.0
        cy = ry + rectangle.get_height()/2.0

        ax.annotate(field['name'], (cx, cy), color='lightgrey',
                    fontsize=11, ha='center', va='center')
        position += field['size']
        if position >= 32:
            currentrow += 1
            position = 0

        if rem > 0:
            rectangle = plt.Rectangle(
                (position, (currentrow - rows)), rem, rowcount, edgecolor='k', fc='none')
            plt.gca().add_patch(rectangle)

            rx, ry = rectangle.get_xy()
            cx = rx + rectangle.get_width()/2.0
            cy = ry + rectangle.get_height()/2.0

            ax.annotate(field['name'], (cx, cy), color='lightgrey',
                        fontsize=11, ha='center', va='center')
            position += rem
            if position >= 32:
                currentrow += 1
                position = 0

    plt.savefig(outname)


class eth_header:
    """
    Ethernet header class.

    ...

    Attributes
    ----------
    eth_dst : dictionary
        destination Ethernet address
    eth_src : dictionary
        source Ethernet address
    eth_type : dictionary
        Ethertype
    eth_empt : dictionary
        dummy bits to align for heatmap plotting
    fields : list
        list of header fields
    arr : numpy array
        array to hold actual bit values for the header
    color_matrix : numpy array
        array to store the matplotlib heatmap generated color values

    """

    eth_dst = {'size': 48, 'color': [],
               'vals': np.zeros(48), 'name': "Destination"}
    eth_src = {'size': 48, 'color': [], 'vals': np.zeros(48), 'name': "Source"}
    eth_type = {'size': 16, 'color': [],
                'vals': np.zeros(16), 'name': "Ethertype"}
    eth_empt = {'size': 16, 'color': [], 'vals': np.zeros(16), 'name': ""}

    fields = [eth_dst,
              eth_src,
              eth_type,
              eth_empt
              ]

    arr = np.zeros(128)
    color_matrix = np.zeros(128)


class ipv4_header:
    """
    IPv4 header class.

    ...

    Attributes
    ----------
    ipv4_ver : dictionary
        ipv4 version
    ipv4_hl : dictionary
        ipv4 header length
    ipv4_tos : dictionary
        ipv4 type of service
    ipv4_tl : dictionary
        ipv4 total length
    ipv4_id : dictionary
        ipv4 identification
    ipv4_rbit : dictionary
        ipv4 reserved flag
    ipv4_dfbit : dictionary
        ipv4 don't fragment flag
    ipv4_mfbit : dictionary
        ipv4 more fragments flag
    ipv4_foff : dictionary
        ipv4 fragment offset
    ipv4_ttl : dictionary
        ipv4 time to live
    ipv4_proto : dictionary
        ipv4 protocol
    ipv4_cksum : dictionary
        ipv4 header checksum
    ipv4_src : dictionary
        ipv4 source address
    ipv4_dst : dictionary
        ipv4 destination address
    ipv4_opt : dictionary
        ipv4 options
    fields : list
        list of header fields
    arr : numpy array
        array to hold actual bit values for the header
    color_matrix : numpy array
        array to store the matplotlib heatmap generated color values

    """

    ipv4_ver = {'size': 4,   'color': [],
                'vals': np.zeros(4),   'name': "Version"}
    ipv4_hl = {'size': 4,   'color': [], 'vals': np.zeros(4),   'name': "IHL"}
    ipv4_tos = {'size': 8,   'color': [], 'vals': np.zeros(8),   'name': "TOS"}
    ipv4_tl = {'size': 16,  'color': [],
               'vals': np.zeros(16),  'name': "Total Length"}
    ipv4_id = {'size': 16,  'color': [], 'vals': np.zeros(16),  'name': "ID"}
    ipv4_rbit = {'size': 1,   'color': [], 'vals': np.zeros(1),   'name': "R"}
    ipv4_dfbit = {'size': 1,   'color': [], 'vals': np.zeros(1),   'name': "D"}
    ipv4_mfbit = {'size': 1,   'color': [], 'vals': np.zeros(1),   'name': "M"}
    ipv4_foff = {'size': 13,  'color': [],
                 'vals': np.zeros(13),  'name': "Frag Offset"}
    ipv4_ttl = {'size': 8,   'color': [], 'vals': np.zeros(8),   'name': "TTL"}
    ipv4_proto = {'size': 8,   'color': [],
                  'vals': np.zeros(8),   'name': "Protocol"}
    ipv4_cksum = {'size': 16,  'color': [],
                  'vals': np.zeros(16),  'name': "Checksum"}
    ipv4_src = {'size': 32,  'color': [],
                'vals': np.zeros(32),  'name': "Source IP"}
    ipv4_dst = {'size': 32,  'color': [],
                'vals': np.zeros(32),  'name': "Destination IP"}
    ipv4_opt = {'size': 320, 'color': [],
                'vals': np.zeros(320), 'name': "Options"}

    fields = [ipv4_ver,
              ipv4_hl,
              ipv4_tos,
              ipv4_tl,
              ipv4_id,
              ipv4_rbit,
              ipv4_dfbit,
              ipv4_mfbit,
              ipv4_foff,
              ipv4_ttl,
              ipv4_proto,
              ipv4_cksum,
              ipv4_src,
              ipv4_dst,
              ipv4_opt
              ]

    arr = np.zeros(480)
    color_matrix = np.zeros(480)


class tcp_header:
    """
    TCP header class.

    ...

    Attributes
    ----------
    tcp_sprt : dictionary
        tcp source port
    tcp_dprt : dictionary
        tcp destination port
    tcp_seq : dictionary
        tcp sequence number
    tcp_ackn : dictionary
        tcp acknowledgement number
    tcp_doff : dictionary
        tcp data offset
    tcp_res : dictionary
        tcp reserved
    tcp_ns : dictionary
        tcp ECN nonce flag
    tcp_cwr : dictionary
        tcp congestion window reduced flag
    tcp_ece : dictionary
        tcp ECN-Echo flag
    tcp_urg : dictionary
        tcp urgent flag
    tcp_ackf : dictionary
        tcp acknowledgement flag
    tcp_psh : dictionary
        tcp push flag
    tcp_rst : dictionary
        tcp reset flag
    tcp_syn : dictionary
        tcp syn flag
    tcp_fin : dictionary
        tcp fin flag
    tcp_wsize : dictionary
        tcp window size
    tcp_cksum : dictionary
        tcp checksum
    tcp_urp : dictionary
        tcp urgent pointer
    tcp_opt : dictionary
        tcp options
    fields : list
        list of header fields
    arr : numpy array
        array to hold actual bit values for the header
    color_matrix : numpy array
        array to store the matplotlib heatmap generated color values

    """

    tcp_sprt = {'size': 16,  'color': [],
                'vals': np.zeros(16),  'name': "Source Port"}
    tcp_dprt = {'size': 16,  'color': [],
                'vals': np.zeros(16),  'name': "Destination Port"}
    tcp_seq = {'size': 32,  'color': [],
               'vals': np.zeros(32),  'name': "Sequence"}
    tcp_ackn = {'size': 32,  'color': [], 'vals': np.zeros(32),  'name': "Ack"}
    tcp_doff = {'size': 4,   'color': [],
                'vals': np.zeros(4),   'name': "Offset"}
    tcp_res = {'size': 3,   'color': [], 'vals': np.zeros(3),   'name': "Rsvd"}
    tcp_ns = {'size': 1,   'color': [], 'vals': np.zeros(1),   'name': "N"}
    tcp_cwr = {'size': 1,   'color': [], 'vals': np.zeros(1),   'name': "C"}
    tcp_ece = {'size': 1,   'color': [], 'vals': np.zeros(1),   'name': "E"}
    tcp_urg = {'size': 1,   'color': [], 'vals': np.zeros(1),   'name': "U"}
    tcp_ackf = {'size': 1,   'color': [], 'vals': np.zeros(1),   'name': "A"}
    tcp_psh = {'size': 1,   'color': [], 'vals': np.zeros(1),   'name': "P"}
    tcp_rst = {'size': 1,   'color': [], 'vals': np.zeros(1),   'name': "R"}
    tcp_syn = {'size': 1,   'color': [], 'vals': np.zeros(1),   'name': "S"}
    tcp_fin = {'size': 1,   'color': [], 'vals': np.zeros(1),   'name': "F"}
    tcp_wsize = {'size': 16,  'color': [],
                 'vals': np.zeros(16),  'name': "Window Size"}
    tcp_cksum = {'size': 16,  'color': [],
                 'vals': np.zeros(16),  'name': "Checksum"}
    tcp_urp = {'size': 16,  'color': [],
               'vals': np.zeros(16),  'name': "Urgent Pointer"}
    tcp_opt = {'size': 320, 'color': [],
               'vals': np.zeros(320), 'name': "Options"}

    fields = [tcp_sprt,
              tcp_dprt,
              tcp_seq,
              tcp_ackn,
              tcp_doff,
              tcp_res,
              tcp_ns,
              tcp_cwr,
              tcp_ece,
              tcp_urg,
              tcp_ackf,
              tcp_psh,
              tcp_rst,
              tcp_syn,
              tcp_fin,
              tcp_wsize,
              tcp_cksum,
              tcp_urp,
              tcp_opt
              ]

    arr = np.zeros(480)
    color_matrix = np.zeros(480)


class udp_header:
    """
    UDP header class.

    ...

    Attributes
    ----------
    udp_sport : dictionary
        udp source port
    udp_dport : dictionary
        udp destination port
    udp_len : dictionary
        udp length
    udp_cksum : dictionary
        udp checksum
    fields : list
        list of header fields
    arr : numpy array
        array to hold actual bit values for the header
    color_matrix : numpy array
        array to store the matplotlib heatmap generated color values

    """

    udp_sport = {'size': 16,  'color': [],
                 'vals': np.zeros(16),  'name': "Source Port"}
    udp_dport = {'size': 16,  'color': [],
                 'vals': np.zeros(16),  'name': "Destination Port"}
    udp_len = {'size': 16,  'color': [],
               'vals': np.zeros(16),  'name': "Length"}
    udp_cksum = {'size': 16,  'color': [],
                 'vals': np.zeros(16),  'name': "Checksum"}

    fields = [udp_sport,
              udp_dport,
              udp_len,
              udp_cksum
              ]

    arr = np.zeros(64)
    color_matrix = np.zeros(64)


class icmp_header:
    """
    ICMP header class.

    ...

    Attributes
    ----------
    icmp_type : dictionary
        icmp type
    icmp_code : dictionary
        icmp code
    icmp_cksum : dictionary
        icmp checksum
    icmp_roh : dictionary
        icmp rest of header
    fields : list
        list of header fields
    arr : numpy array
        array to hold actual bit values for the header
    color_matrix : numpy array
        array to store the matplotlib heatmap generated color values

    """

    icmp_type = {'size': 8,   'color': [],
                 'vals': np.zeros(8),   'name': "Type"}
    icmp_code = {'size': 8,   'color': [],
                 'vals': np.zeros(8),   'name': "Code"}
    icmp_cksum = {'size': 16,  'color': [],
                  'vals': np.zeros(16),  'name': "Checksum"}
    icmp_roh = {'size': 32,  'color': [],
                'vals': np.zeros(32),  'name': "Rest of Header"}
    # Can also include ICMP data field by uncommenting below and increasing the arr and color_matrix to 480 each
    # icmp_data =  {'size': 416, 'color': [], 'vals': np.zeros(416), 'name': "Data"}

    fields = [icmp_type,
              icmp_code,
              icmp_cksum,
              icmp_roh
              # icmp_data
              ]

    arr = np.zeros(64)
    color_matrix = np.zeros(64)


class payload_header:
    """
    Payload class.

    ...

    Attributes
    ----------
    payload_data : dictionary
        payload
    fields : list
        list of header fields
    arr : numpy array
        array to hold actual bit values for the header
    color_matrix : numpy array
        array to store the matplotlib heatmap generated color values

    """

    # Field bitmaps
    payload_data = {'size': 480, 'color': [],
                    'vals': np.zeros(480), 'name': "Payload"}

    fields = [payload_data]

    # Arr holds the actual bit values for the header
    arr = np.zeros(480)
    # Color matrix stores the matplotlib generated color values
    color_matrix = np.zeros(480)

def make_heatmaps(model_path, out_path):

    ethhead = eth_header()
    iphead = ipv4_header()
    tcphead = tcp_header()
    udphead = udp_header()
    icmphead = icmp_header()
    payloadhead = payload_header()

    with open(model_path, 'rb') as fin:
        ob = pickle.load(fin)
        d = ob.get_model_feature_importance()
        
    for key, val in d.items():
        header, field, bit = key.split('_')

        if header == 'ipv4':
            headkey = header + "_" + field
            getattr(iphead, headkey)['vals'][int(bit)] += val
        elif header == 'eth':
            headkey = header + "_" + field
            getattr(ethhead, headkey)['vals'][int(bit)] += val
        elif header == 'tcp':
            if field == 'ack':
                field = 'ackf'
            headkey = header + "_" + field
            getattr(tcphead, headkey)['vals'][int(bit)] += val
        elif header == 'udp':
            headkey = header + "_" + field
            getattr(udphead, headkey)['vals'][int(bit)] += val
        elif header == 'icmp':
            headkey = header + "_" + field
            getattr(icmphead, headkey)['vals'][int(bit)] += val
        elif header == 'payload':
            headkey = header + "_" + field
            getattr(payloadhead, headkey)['vals'][int(bit)] += val
        
    
    setArray(ethhead)
    setArray(iphead)
    setArray(tcphead)
    setArray(udphead)
    setArray(icmphead)
    setArray(payloadhead)

    out_path.mkdir(parents=True, exist_ok=True)
    
    getHeatmap(ethhead, out_path / 'ethheat.pdf')
    getHeatmap(iphead, out_path / 'ipv4heat.pdf')
    getHeatmap(tcphead, out_path / 'tcpheat.pdf')
    getHeatmap(udphead, out_path / 'udpheat.pdf')
    getHeatmap(icmphead, out_path / 'icmpheat.pdf')
    getHeatmap(payloadhead, out_path / 'payloadheat.pdf')