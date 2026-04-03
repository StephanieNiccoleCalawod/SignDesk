"""
test_landmarks.py - Synthetic & Reference Landmark Data for Testing

Provides programmatically generated "ideal" landmark positions for
ASL gestures, based on the finger-state rules defined in library.py.

MediaPipe landmarks are normalized to [0, 1] with:
  - x: left(0) → right(1)
  - y: top(0) → bottom(1)
  - z: depth (closer = negative)

Convention used here:
  - Extended finger: tip.y < pip.y (tip is higher on screen)
  - Curled finger:   tip.y > pip.y (tip is lower / closer to palm)
  - Thumb extended:  tip.x < ip.x  (for mirrored/right hand view)
"""


def _base_hand():
    """
    Baseline right-hand landmark positions (palm facing camera, mirrored).
    Returns list of 21 (x, y, z) tuples.

    Index map:
      0: WRIST
      1-4: THUMB (CMC, MCP, IP, TIP)
      5-8: INDEX (MCP, PIP, DIP, TIP)
      9-12: MIDDLE (MCP, PIP, DIP, TIP)
      13-16: RING (MCP, PIP, DIP, TIP)
      17-20: PINKY (MCP, PIP, DIP, TIP)
    """
    return [
        (0.50, 0.85, 0.00),   # 0  WRIST
        (0.62, 0.75, 0.00),   # 1  THUMB_CMC
        (0.68, 0.65, 0.00),   # 2  THUMB_MCP
        (0.72, 0.55, 0.00),   # 3  THUMB_IP
        (0.75, 0.48, 0.00),   # 4  THUMB_TIP
        (0.55, 0.55, 0.00),   # 5  INDEX_MCP
        (0.55, 0.40, 0.00),   # 6  INDEX_PIP
        (0.55, 0.30, 0.00),   # 7  INDEX_DIP
        (0.55, 0.22, 0.00),   # 8  INDEX_TIP
        (0.48, 0.53, 0.00),   # 9  MIDDLE_MCP
        (0.48, 0.38, 0.00),   # 10 MIDDLE_PIP
        (0.48, 0.28, 0.00),   # 11 MIDDLE_DIP
        (0.48, 0.20, 0.00),   # 12 MIDDLE_TIP
        (0.41, 0.55, 0.00),   # 13 RING_MCP
        (0.41, 0.40, 0.00),   # 14 RING_PIP
        (0.41, 0.30, 0.00),   # 15 RING_DIP
        (0.41, 0.22, 0.00),   # 16 RING_TIP
        (0.35, 0.58, 0.00),   # 17 PINKY_MCP
        (0.35, 0.45, 0.00),   # 18 PINKY_PIP
        (0.35, 0.36, 0.00),   # 19 PINKY_DIP
        (0.35, 0.28, 0.00),   # 20 PINKY_TIP
    ]


def _curl_finger(lm, tip_idx, pip_idx, mcp_idx):
    """Curl a finger: bend PIP up, tip tucks back to MCP. Avoids pointing down."""
    mcp = lm[mcp_idx]
    lm[pip_idx] = (mcp[0], mcp[1] - 0.06, mcp[2] - 0.05)   # PIP UP
    lm[tip_idx - 1] = (mcp[0], mcp[1] - 0.02, mcp[2])      # DIP down toward palm
    lm[tip_idx] = (mcp[0], mcp[1] - 0.01, mcp[2] + 0.05)   # TIP tucked ABOVE or AT MCP level


def _extend_finger(lm, tip_idx, pip_idx, mcp_idx):
    """Extend a finger by moving tip well above PIP."""
    mcp = lm[mcp_idx]
    lm[pip_idx] = (mcp[0], mcp[1] - 0.15, mcp[2])
    lm[tip_idx - 1] = (mcp[0], mcp[1] - 0.25, mcp[2])   # DIP
    lm[tip_idx] = (mcp[0], mcp[1] - 0.33, mcp[2])        # TIP


def _curl_thumb(lm):
    """Curl thumb: tip.x > ip.x (library reads this as NOT extended)."""
    lm[3] = (0.60, 0.55, 0.0)   # THUMB_IP
    lm[4] = (0.68, 0.58, 0.0)   # THUMB_TIP — x(0.68) > ip_x(0.60) = NOT extended


def _extend_thumb(lm):
    """Extend thumb: tip.x < ip.x (library reads this as extended)."""
    lm[3] = (0.68, 0.55, 0.0)   # THUMB_IP
    lm[4] = (0.58, 0.48, 0.0)   # THUMB_TIP — x(0.58) < ip_x(0.68) = extended


# ══════════════════════════════════════════════════════════════
# SYNTHETIC ASL GESTURE LANDMARKS
#
# KEY INSIGHT: Many gestures (A, E, S, M, N, T) are fist variants.
# The library distinguishes them via:
#   A: thumb extended/alongside, fingers curled tightly
#   E: thumb NOT extended, thumb tip BELOW index tip, high curl
#   S: thumb NOT extended, thumb tip ABOVE index PIP
#   M: thumb under, 3 fingertips close together below MCPs
#   N: thumb under middle MCP, 2 fingertips close
#   T: thumb between index/middle MCPs, above PIP
# ══════════════════════════════════════════════════════════════

def make_A():
    """ASL 'A': Fist with thumb alongside (thumb up beside index)."""
    lm = _base_hand()
    _curl_finger(lm, 8, 6, 5)
    _curl_finger(lm, 12, 10, 9)
    _curl_finger(lm, 16, 14, 13)
    _curl_finger(lm, 20, 18, 17)
    # A-specific: Thumb NOT extended radially to avoid P/T matching, but tip ABOVE index MCP
    lm[3] = (0.60, 0.55, 0.0)       # IP
    lm[4] = (0.65, 0.48, 0.0)       # TIP: x(0.65) > ip.x(0.60) = not extended; y(0.48) < index_mcp(0.55)
    return lm


def make_B():
    """ASL 'B': All four fingers extended upward, thumb tucked."""
    lm = _base_hand()
    _extend_finger(lm, 8, 6, 5)
    _extend_finger(lm, 12, 10, 9)
    _extend_finger(lm, 16, 14, 13)
    _extend_finger(lm, 20, 18, 17)
    _curl_thumb(lm)
    # Fingers close together (spread < 0.15 per check_B)
    lm[8]  = (0.52, 0.22, 0.0)   # INDEX_TIP
    lm[12] = (0.50, 0.20, 0.0)   # MIDDLE_TIP
    lm[16] = (0.48, 0.22, 0.0)   # RING_TIP
    lm[20] = (0.46, 0.25, 0.0)   # PINKY_TIP  spread = |0.52-0.46| = 0.06 < 0.15
    return lm


def make_C():
    """ASL 'C': Curved hand forming C shape (partially curled)."""
    lm = _base_hand()
    # Set curl values between 0.15 and 0.7 for all fingers
    for tip, dip, pip, mcp in [(8,7,6,5), (12,11,10,9), (16,15,14,13), (20,19,18,17)]:
        m = lm[mcp]
        lm[pip] = (m[0] - 0.02, m[1] - 0.05, m[2] - 0.02)
        lm[dip] = (m[0] - 0.04, m[1] - 0.07, m[2] - 0.01)
        lm[tip] = (m[0] - 0.05, m[1] - 0.09, m[2] + 0.02)  # tip.y < pip.y so A fails (extended)
    # Thumb extended: tip.x < ip.x
    lm[3] = (0.72, 0.55, 0.0)   # IP
    lm[4] = (0.60, 0.58, 0.0)   # TIP: x(0.60) < ip.x(0.72) = extended. y(0.58) > MCP(0.55) to fail A!
    # Gap between thumb and index > 0.08
    lm[8] = (0.50, 0.58, 0.0)   # index tip
    return lm


def make_D():
    """ASL 'D': Index up, others curled, thumb touches middle fingertip."""
    lm = _base_hand()
    _extend_finger(lm, 8, 6, 5)    # index extended up
    _curl_finger(lm, 12, 10, 9)    # middle curled
    _curl_finger(lm, 16, 14, 13)   # ring curled
    _curl_finger(lm, 20, 18, 17)   # pinky curled
    # Thumb tip touches middle fingertip (dist < 0.08)
    lm[12] = (0.50, 0.63, 0.0)    # middle tip position
    lm[4] = (0.48, 0.63, 0.0)     # thumb tip — very close, and tip.x < ip.x
    lm[3] = (0.60, 0.55, 0.0)     # IP has higher x
    return lm


def make_E():
    """ASL 'E': All fingers curled, thumb tucked below fingertips."""
    lm = _base_hand()
    _curl_finger(lm, 8, 6, 5)
    _curl_finger(lm, 12, 10, 9)
    _curl_finger(lm, 16, 14, 13)
    _curl_finger(lm, 20, 18, 17)
    # E-specific: thumb NOT extended, thumb tip BELOW index tip, tight curl
    lm[3] = (0.60, 0.55, 0.0)       # IP
    lm[4] = (0.65, 0.72, 0.0)       # Thumb tip: x(0.65) > ip(0.60)=not ext; y(0.72) is low
    # Index TIP y must be < Thumb TIP y
    lm[8] = (0.55, 0.65, 0.0)       # Index tip y(0.65) < Thumb tip y(0.72)
    return lm


def make_F():
    """ASL 'F': Index+thumb touching circle, other three extended."""
    lm = _base_hand()
    _extend_finger(lm, 12, 10, 9)   # middle extended
    _extend_finger(lm, 16, 14, 13)  # ring extended
    _extend_finger(lm, 20, 18, 17)  # pinky extended
    # Index curled — tip touching thumb (dist < 0.06)
    _curl_finger(lm, 8, 6, 5)
    lm[4] = (0.56, 0.64, 0.0)    # thumb tip
    lm[8] = (0.57, 0.65, 0.0)    # index tip — dist ≈ 0.014
    return lm


def make_G():
    """ASL 'G': Index and thumb pointing sideways."""
    lm = _base_hand()
    _extend_thumb(lm)
    # Index pointing sideways (horizontal > vertical displacement)
    lm[5] = (0.50, 0.55, 0.0)     # INDEX_MCP
    lm[6] = (0.60, 0.54, 0.0)     # INDEX_PIP (tip.y < pip.y = "extended")
    lm[7] = (0.70, 0.53, 0.0)
    lm[8] = (0.80, 0.52, 0.0)     # tip far right (horiz > vert)
    _curl_finger(lm, 12, 10, 9)
    _curl_finger(lm, 16, 14, 13)
    _curl_finger(lm, 20, 18, 17)
    return lm


def make_H():
    """ASL 'H': Index and middle extended sideways together."""
    lm = _base_hand()
    # Index sideways
    lm[5] = (0.50, 0.55, 0.0)
    lm[6] = (0.60, 0.54, 0.0)
    lm[7] = (0.70, 0.53, 0.0)
    lm[8] = (0.80, 0.52, 0.0)
    # Middle sideways
    lm[9]  = (0.48, 0.53, 0.0)
    lm[10] = (0.58, 0.52, 0.0)
    lm[11] = (0.68, 0.51, 0.0)
    lm[12] = (0.78, 0.50, 0.0)
    _curl_finger(lm, 16, 14, 13)
    _curl_finger(lm, 20, 18, 17)
    return lm


def make_I():
    """ASL 'I': Pinky extended, all others curled, thumb tucked."""
    lm = _base_hand()
    _curl_finger(lm, 8, 6, 5)
    _curl_finger(lm, 12, 10, 9)
    _curl_finger(lm, 16, 14, 13)
    _extend_finger(lm, 20, 18, 17)   # ONLY pinky extended
    # CRITICAL: thumb NOT extended (this differentiates I from Y)
    _curl_thumb(lm)
    return lm


def make_K():
    """ASL 'K': Index+middle in V shape, thumb extended between them."""
    lm = _base_hand()
    _extend_finger(lm, 8, 6, 5)     # index up
    _extend_finger(lm, 12, 10, 9)   # middle up
    _curl_finger(lm, 16, 14, 13)
    _curl_finger(lm, 20, 18, 17)
    _extend_thumb(lm)
    # V-spread > 0.05  AND  thumb between them
    lm[8]  = (0.60, 0.22, 0.0)      # index tip right
    lm[12] = (0.40, 0.20, 0.0)      # middle tip left — spread = 0.20
    # Thumb tip between index and middle, tip.x < ip.x
    lm[3] = (0.58, 0.40, 0.0)       # IP
    lm[4] = (0.50, 0.35, 0.0)       # TIP: x(0.50) < ip(0.58) = extended
    return lm


def make_L():
    """ASL 'L': Index up, thumb out, forming L-shape."""
    lm = _base_hand()
    _extend_finger(lm, 8, 6, 5)     # index UP
    _curl_finger(lm, 12, 10, 9)
    _curl_finger(lm, 16, 14, 13)
    _curl_finger(lm, 20, 18, 17)
    # CRITICAL: thumb extended (tip.x < ip.x)
    _extend_thumb(lm)
    # Strong L-shape: index vertical, thumb horizontal
    lm[8] = (0.55, 0.18, 0.0)       # index tip HIGH up
    # thumb: tip at lower x than CMC = pointing outward
    lm[1] = (0.62, 0.75, 0.0)       # THUMB_CMC
    lm[3] = (0.68, 0.55, 0.0)       # THUMB_IP
    lm[4] = (0.35, 0.48, 0.0)       # THUMB_TIP: x < ip.x = extended; far outwards so NOT touching middle!
    return lm


def make_M():
    """ASL 'M': Three fingers over thumb, all curled."""
    lm = _base_hand()
    _curl_finger(lm, 8, 6, 5)
    _curl_finger(lm, 12, 10, 9)
    _curl_finger(lm, 16, 14, 13)
    _curl_finger(lm, 20, 18, 17)
    # M-specific: thumb tucked under (y > index MCP y=0.55)
    lm[3] = (0.55, 0.58, 0.0)       # IP
    lm[4] = (0.60, 0.62, 0.0)       # thumb tip: x(0.60) > ip.x(0.55) = not extended
    # Three fingertips close together (<0.06)
    lm[8]  = (0.53, 0.63, 0.0)      # index tip
    lm[12] = (0.50, 0.63, 0.0)      # middle tip  — dist to index < 0.06
    lm[16] = (0.47, 0.63, 0.0)      # ring tip    — dist to middle < 0.06
    return lm


def make_N():
    """ASL 'N': Two fingers over thumb, curled."""
    lm = _base_hand()
    _curl_finger(lm, 8, 6, 5)
    _curl_finger(lm, 12, 10, 9)
    _curl_finger(lm, 16, 14, 13)
    _curl_finger(lm, 20, 18, 17)
    # N-specific: thumb below MIDDLE_MCP (y=0.53)
    lm[3] = (0.52, 0.56, 0.0)       # IP
    lm[4] = (0.56, 0.60, 0.0)       # tip: x(0.56)>ip.x(0.52)=not ext; y(0.60)>0.53
    # Index and middle tips close (< 0.06)
    lm[8]  = (0.52, 0.62, 0.0)
    lm[12] = (0.49, 0.62, 0.0)      # dist = 0.03 < 0.06
    return lm


def make_O():
    """ASL 'O': All fingertips touching thumb forming O."""
    lm = _base_hand()
    # Thumb NOT extended for O (tip.x > ip.x) so check_A doesn't win
    lm[3] = (0.50, 0.53, 0.0)     # IP
    lm[4]  = (0.54, 0.55, 0.0)    # thumb tip: x(0.54) > ip.x(0.50) = NOT extended
    # Curled to get >0.15 curl ratio, but KEEP tip.y > pip.y so states=False
    for tip, dip, pip, mcp in [(8,7,6,5), (12,11,10,9), (16,15,14,13), (20,19,18,17)]:
        m = lm[mcp]
        lm[pip] = (m[0] - 0.01, m[1] - 0.06, m[2] - 0.02)
        lm[dip] = (m[0] - 0.02, m[1] - 0.02, m[2] - 0.01)
        lm[tip] = (m[0] - 0.03, m[1] + 0.01, m[2] + 0.02)  # tip.y > pip.y so it is "curled"
    
    # Custom thumb position
    lm[3] = (0.50, 0.53, 0.0)      # IP
    lm[4] = (0.54, 0.55, 0.0)      # TIP
    # Spread the fingertips around the thumb to maintain dist < 0.08 for O
    # BUT keep dist(index, middle) > 0.06 to definitively fail N
    lm[8] =  (0.48, 0.55, 0.0)     # index left of thumb -> dist to thumb=0.06
    lm[12] = (0.60, 0.55, 0.0)     # middle right of thumb -> dist to thumb=0.06
    lm[16] = (0.52, 0.49, 0.0)     # ring above thumb -> dist=0.06
    lm[20] = (0.56, 0.60, 0.0)     # pinky below thumb
    return lm


def make_P():
    """ASL 'P': Like K but pointing downward."""
    lm = _base_hand()
    # Index pointing DOWN (tip.y > mcp.y)
    lm[5] = (0.55, 0.50, 0.0)
    lm[6] = (0.56, 0.60, 0.0)
    lm[7] = (0.56, 0.70, 0.0)
    lm[8] = (0.56, 0.82, 0.0)    # tip well below MCP
    # Middle pointing DOWN
    lm[9]  = (0.48, 0.50, 0.0)
    lm[10] = (0.49, 0.60, 0.0)
    lm[11] = (0.49, 0.70, 0.0)
    lm[12] = (0.49, 0.82, 0.0)
    _curl_finger(lm, 16, 14, 13)
    _curl_finger(lm, 20, 18, 17)
    _extend_thumb(lm)
    return lm


def make_Q():
    """ASL 'Q': Like G but pointing downward."""
    lm = _base_hand()
    # Index pointing DOWN
    lm[5] = (0.55, 0.50, 0.0)
    lm[6] = (0.55, 0.60, 0.0)
    lm[7] = (0.55, 0.70, 0.0)
    lm[8] = (0.55, 0.82, 0.0)
    # Thumb pointing DOWN
    lm[2] = (0.65, 0.60, 0.0)
    lm[3] = (0.65, 0.70, 0.0)
    lm[4] = (0.65, 0.82, 0.0)
    _curl_finger(lm, 12, 10, 9)
    _curl_finger(lm, 16, 14, 13)
    _curl_finger(lm, 20, 18, 17)
    return lm


def make_R():
    """ASL 'R': Index and middle extended, crossed (tips touching)."""
    lm = _base_hand()
    _extend_finger(lm, 8, 6, 5)
    _extend_finger(lm, 12, 10, 9)
    _curl_finger(lm, 16, 14, 13)
    _curl_finger(lm, 20, 18, 17)
    # Tips VERY close (< 0.04) = crossed
    lm[8]  = (0.505, 0.22, 0.0)
    lm[12] = (0.510, 0.21, 0.0)   # dist ≈ 0.011  well < 0.04
    return lm


def make_S():
    """ASL 'S': Fist with thumb over curled fingers."""
    lm = _base_hand()
    _curl_finger(lm, 8, 6, 5)
    _curl_finger(lm, 12, 10, 9)
    _curl_finger(lm, 16, 14, 13)
    _curl_finger(lm, 20, 18, 17)
    # S-specific: thumb wrapped across index and middle
    lm[3] = (0.55, 0.55, 0.0)       # IP moves inward
    # tip: x(0.40) is tightly crossed over index (0.55) and middle (0.53)
    lm[4] = (0.40, 0.46, 0.0)       
    return lm


def make_T():
    """ASL 'T': Thumb between index and middle (fist, thumb above PIP)."""
    lm = _base_hand()
    _curl_finger(lm, 8, 6, 5)
    _curl_finger(lm, 12, 10, 9)
    _curl_finger(lm, 16, 14, 13)
    _curl_finger(lm, 20, 18, 17)
    # T-specific: thumb x between index MCP and middle MCP, tip above PIP
    idx_x = lm[5][0]   # ~0.55
    mid_x = lm[9][0]   # ~0.48
    thumb_x = (idx_x + mid_x) / 2  # ~0.515
    # Thumb NOT extended (tip.x > ip.x)
    lm[3] = (0.50, 0.52, 0.0)       # IP: x < thumb_x
    lm[4] = (thumb_x, lm[6][1] - 0.02, 0.0)  # TIP: x(0.515) > ip.x(0.50) = not ext
    return lm


def make_U():
    """ASL 'U': Index and middle extended together (close), others curled."""
    lm = _base_hand()
    _extend_finger(lm, 8, 6, 5)
    _extend_finger(lm, 12, 10, 9)
    _curl_finger(lm, 16, 14, 13)
    _curl_finger(lm, 20, 18, 17)
    # U-specific: tips close but > 0.04 (R threshold). R requires < 0.04
    # spread = 0.045 → U wins (< 0.05), R loses (> 0.04)
    lm[8]  = (0.525, 0.22, 0.0)
    lm[12] = (0.480, 0.22, 0.0)     # dist = 0.045
    return lm


def make_V():
    """ASL 'V': Index and middle in V-shape (peace sign)."""
    lm = _base_hand()
    _extend_finger(lm, 8, 6, 5)
    _extend_finger(lm, 12, 10, 9)
    _curl_finger(lm, 16, 14, 13)
    _curl_finger(lm, 20, 18, 17)
    # V-specific: tips SPREAD (spread > 0.06)
    lm[8]  = (0.60, 0.22, 0.0)     # index tip far right
    lm[12] = (0.38, 0.20, 0.0)     # middle tip far left  — spread = 0.22
    return lm


def make_W():
    """ASL 'W': Index, middle, ring extended and spread."""
    lm = _base_hand()
    _extend_finger(lm, 8, 6, 5)
    _extend_finger(lm, 12, 10, 9)
    _extend_finger(lm, 16, 14, 13)
    _curl_finger(lm, 20, 18, 17)
    # W-specific: all three spread > 0.04
    lm[8]  = (0.58, 0.22, 0.0)
    lm[12] = (0.48, 0.20, 0.0)     # spread1 = 0.10
    lm[16] = (0.38, 0.22, 0.0)     # spread2 = 0.10
    return lm


def make_X():
    """ASL 'X': Index hooked (PIP raised, tip bent below DIP)."""
    lm = _base_hand()
    _curl_finger(lm, 12, 10, 9)
    _curl_finger(lm, 16, 14, 13)
    _curl_finger(lm, 20, 18, 17)
    _curl_thumb(lm)
    # X-specific: PIP above MCP (0.42 < 0.55), DIP above PIP
    # BUT TIP below DIP (hooked: 0.44 > 0.38)
    lm[5] = (0.55, 0.55, 0.0)       # INDEX_MCP
    lm[6] = (0.55, 0.42, 0.0)       # INDEX_PIP  (above MCP)
    lm[7] = (0.55, 0.38, 0.0)       # INDEX_DIP
    lm[8] = (0.55, 0.44, 0.0)       # INDEX_TIP hooked (0.44 > 0.38)
    # Ensure thumb NOT extended for X
    lm[3] = (0.60, 0.55, 0.0)       # IP
    lm[4] = (0.65, 0.58, 0.0)       # tip: x(0.65)>ip(0.60) = not extended
    return lm


def make_Y():
    """ASL 'Y': Thumb and pinky extended, others curled (shaka)."""
    lm = _base_hand()
    # CRITICAL: BOTH thumb AND pinky extended (differentiates from I)
    _extend_thumb(lm)
    _extend_finger(lm, 20, 18, 17)   # pinky extended
    _curl_finger(lm, 8, 6, 5)        # index curled
    _curl_finger(lm, 12, 10, 9)      # middle curled
    _curl_finger(lm, 16, 14, 13)     # ring curled
    return lm


# ══════════════════════════════════════════════════════════════
# REGISTRY — maps letter to landmark generator
# ══════════════════════════════════════════════════════════════

SYNTHETIC_GESTURES = {
    "A": make_A, "B": make_B, "C": make_C, "D": make_D,
    "E": make_E, "F": make_F, "G": make_G, "H": make_H,
    "I": make_I, "K": make_K, "L": make_L, "M": make_M,
    "N": make_N, "O": make_O, "P": make_P, "Q": make_Q,
    "R": make_R, "S": make_S, "T": make_T, "U": make_U,
    "V": make_V, "W": make_W, "X": make_X, "Y": make_Y,
}


def make_garbage_landmarks():
    """Random-ish landmarks that don't match any real gesture."""
    return [(0.5, 0.5, 0.0)] * 21


def make_partial_landmarks():
    """Only 10 landmarks — invalid input (should be rejected)."""
    return [(0.5, 0.5, 0.0)] * 10
