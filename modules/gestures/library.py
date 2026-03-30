"""
library.py - ASL Gesture Library
Predefined ASL alphabet gesture definitions using finger state rules.
Maps to: SD003 (Gesture Recognition Library)

Each gesture is defined by a set of finger states and positional rules
based on the 21 MediaPipe hand landmarks.

MediaPipe Landmark Indices:
    0: WRIST
    1-4: THUMB (CMC, MCP, IP, TIP)
    5-8: INDEX (MCP, PIP, DIP, TIP)
    9-12: MIDDLE (MCP, PIP, DIP, TIP)
    13-16: RING (MCP, PIP, DIP, TIP)
    17-20: PINKY (MCP, PIP, DIP, TIP)
"""

# Landmark index constants for readability
WRIST = 0
THUMB_CMC = 1; THUMB_MCP = 2; THUMB_IP = 3; THUMB_TIP = 4
INDEX_MCP = 5; INDEX_PIP = 6; INDEX_DIP = 7; INDEX_TIP = 8
MIDDLE_MCP = 9; MIDDLE_PIP = 10; MIDDLE_DIP = 11; MIDDLE_TIP = 12
RING_MCP = 13; RING_PIP = 14; RING_DIP = 15; RING_TIP = 16
PINKY_MCP = 17; PINKY_PIP = 18; PINKY_DIP = 19; PINKY_TIP = 20

# Finger groups for convenience
FINGER_TIPS = [THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]
FINGER_PIPS = [THUMB_IP, INDEX_PIP, MIDDLE_PIP, RING_PIP, PINKY_PIP]
FINGER_MCPS = [THUMB_MCP, INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP]


def _distance(p1, p2):
    """Euclidean distance between two (x, y, z) landmark points."""
    return ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2 + (p1[2] - p2[2])**2) ** 0.5


def _distance_2d(p1, p2):
    """2D Euclidean distance (ignoring z)."""
    return ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2) ** 0.5


def get_finger_states(landmarks):
    """
    Determines which fingers are extended (True) or curled (False).
    Returns dict: {thumb, index, middle, ring, pinky}

    For thumb: compare tip x-position relative to IP joint (accounts for left/right hand).
    For other fingers: tip is above (lower y value) PIP joint = extended.
    """
    lm = landmarks

    # Determine hand orientation (left vs right) based on thumb direction
    # If thumb tip is to the right of thumb MCP, it's likely a right hand view
    thumb_extended = lm[THUMB_TIP][0] < lm[THUMB_IP][0]  # Adjusted for mirrored

    # For fingers: lower y = higher on screen = extended
    index_extended = lm[INDEX_TIP][1] < lm[INDEX_PIP][1]
    middle_extended = lm[MIDDLE_TIP][1] < lm[MIDDLE_PIP][1]
    ring_extended = lm[RING_TIP][1] < lm[RING_PIP][1]
    pinky_extended = lm[PINKY_TIP][1] < lm[PINKY_PIP][1]

    return {
        "thumb": thumb_extended,
        "index": index_extended,
        "middle": middle_extended,
        "ring": ring_extended,
        "pinky": pinky_extended,
    }


def get_finger_curl(landmarks):
    """
    Returns a curl ratio for each finger (0.0 = fully extended, 1.0 = fully curled).
    Uses the distance from fingertip to MCP relative to finger length.
    """
    lm = landmarks

    def curl_ratio(tip, pip, mcp):
        full_length = _distance(lm[mcp], lm[pip]) + _distance(lm[pip], lm[tip])
        if full_length < 0.001:
            return 0.0
        direct = _distance(lm[mcp], lm[tip])
        ratio = direct / full_length
        # Invert: small ratio = curled, large = extended
        return max(0.0, min(1.0, 1.0 - ratio))

    return {
        "index": curl_ratio(INDEX_TIP, INDEX_PIP, INDEX_MCP),
        "middle": curl_ratio(MIDDLE_TIP, MIDDLE_PIP, MIDDLE_MCP),
        "ring": curl_ratio(RING_TIP, RING_PIP, RING_MCP),
        "pinky": curl_ratio(PINKY_TIP, PINKY_PIP, PINKY_MCP),
    }


# ──────────────────────────────────────────────────────────────
# ASL GESTURE DEFINITIONS (A-Z Static Signs)
# ──────────────────────────────────────────────────────────────
#
# Each gesture function takes landmarks (list of 21 (x,y,z) tuples)
# and returns a confidence score (0.0 to 1.0).
# Returns 0.0 if the gesture clearly doesn't match.
#
# Note: Letters J and Z require motion and are excluded from
# single-frame recognition. They are noted as "motion-required".
# ──────────────────────────────────────────────────────────────

def check_A(landmarks):
    """ASL 'A': Fist with thumb alongside (thumb up beside index)."""
    lm = landmarks
    states = get_finger_states(lm)
    curl = get_finger_curl(lm)

    score = 0.0
    # All four fingers curled
    if not states["index"] and not states["middle"] and not states["ring"] and not states["pinky"]:
        score += 0.5
    # Thumb should be extended or beside the fist (not tucked)
    if states["thumb"] or lm[THUMB_TIP][1] < lm[INDEX_MCP][1]:
        score += 0.3
    # Fingers tightly curled
    if curl["index"] > 0.4 and curl["middle"] > 0.4:
        score += 0.2

    return min(score, 1.0)


def check_B(landmarks):
    """ASL 'B': All four fingers extended upward, thumb tucked across palm."""
    lm = landmarks
    states = get_finger_states(lm)

    score = 0.0
    # Four fingers extended
    if states["index"] and states["middle"] and states["ring"] and states["pinky"]:
        score += 0.5
    # Thumb not extended (tucked across palm)
    if not states["thumb"]:
        score += 0.3
    # Fingers close together (index and pinky x-distance small)
    finger_spread = abs(lm[INDEX_TIP][0] - lm[PINKY_TIP][0])
    if finger_spread < 0.15:
        score += 0.2

    return min(score, 1.0)


def check_C(landmarks):
    """ASL 'C': Curved hand forming a C shape."""
    lm = landmarks
    states = get_finger_states(lm)
    curl = get_finger_curl(lm)

    score = 0.0
    # Fingers partially curled (not fully extended, not fully curled)
    mid_curl = all(0.15 < curl[f] < 0.7 for f in ["index", "middle", "ring", "pinky"])
    if mid_curl:
        score += 0.5
    # Thumb extended outward
    if states["thumb"]:
        score += 0.25
    # Gap between thumb and index (C shape opening)
    gap = _distance_2d(lm[THUMB_TIP], lm[INDEX_TIP])
    if gap > 0.08:
        score += 0.25

    return min(score, 1.0)


def check_D(landmarks):
    """ASL 'D': Index finger pointing up, others curled, thumb touches middle."""
    lm = landmarks
    states = get_finger_states(lm)

    score = 0.0
    # Index extended
    if states["index"]:
        score += 0.4
    # Middle, ring, pinky curled
    if not states["middle"] and not states["ring"] and not states["pinky"]:
        score += 0.3
    # Thumb touches or near middle finger
    thumb_mid_dist = _distance_2d(lm[THUMB_TIP], lm[MIDDLE_TIP])
    if thumb_mid_dist < 0.08:
        score += 0.3

    return min(score, 1.0)


def check_E(landmarks):
    """ASL 'E': All fingers curled, thumb tucked below fingers."""
    lm = landmarks
    states = get_finger_states(lm)
    curl = get_finger_curl(lm)

    score = 0.0
    # All fingers curled
    if not states["index"] and not states["middle"] and not states["ring"] and not states["pinky"]:
        score += 0.4
    # Thumb tucked (not extended)
    if not states["thumb"]:
        score += 0.2
    # Fingertips close to palm (high curl values)
    if all(curl[f] > 0.3 for f in ["index", "middle", "ring", "pinky"]):
        score += 0.2
    # Thumb tip below index fingertip
    if lm[THUMB_TIP][1] > lm[INDEX_TIP][1]:
        score += 0.2

    return min(score, 1.0)


def check_F(landmarks):
    """ASL 'F': Index and thumb touching circle, other three fingers extended."""
    lm = landmarks
    states = get_finger_states(lm)

    score = 0.0
    # Middle, ring, pinky extended
    if states["middle"] and states["ring"] and states["pinky"]:
        score += 0.4
    # Index curled or touching thumb
    thumb_index_dist = _distance_2d(lm[THUMB_TIP], lm[INDEX_TIP])
    if thumb_index_dist < 0.06:
        score += 0.4
    # Index not fully extended
    if not states["index"]:
        score += 0.2

    return min(score, 1.0)


def check_G(landmarks):
    """ASL 'G': Index finger and thumb pointing sideways (like pointing)."""
    lm = landmarks
    states = get_finger_states(lm)

    score = 0.0
    # Index extended
    if states["index"]:
        score += 0.3
    # Thumb extended
    if states["thumb"]:
        score += 0.2
    # Middle, ring, pinky curled
    if not states["middle"] and not states["ring"] and not states["pinky"]:
        score += 0.3
    # Index pointing sideways (tip x far from MCP x)
    index_horizontal = abs(lm[INDEX_TIP][0] - lm[INDEX_MCP][0])
    index_vertical = abs(lm[INDEX_TIP][1] - lm[INDEX_MCP][1])
    if index_horizontal > index_vertical:
        score += 0.2

    return min(score, 1.0)


def check_H(landmarks):
    """ASL 'H': Index and middle fingers extended sideways together."""
    lm = landmarks
    states = get_finger_states(lm)

    score = 0.0
    # Index and middle extended
    if states["index"] and states["middle"]:
        score += 0.4
    # Ring and pinky curled
    if not states["ring"] and not states["pinky"]:
        score += 0.3
    # Fingers pointing sideways
    index_horizontal = abs(lm[INDEX_TIP][0] - lm[INDEX_MCP][0])
    index_vertical = abs(lm[INDEX_TIP][1] - lm[INDEX_MCP][1])
    if index_horizontal > index_vertical:
        score += 0.3

    return min(score, 1.0)


def check_I(landmarks):
    """ASL 'I': Pinky extended, all others curled."""
    lm = landmarks
    states = get_finger_states(lm)

    score = 0.0
    # Pinky extended
    if states["pinky"]:
        score += 0.5
    # All others curled
    if not states["index"] and not states["middle"] and not states["ring"]:
        score += 0.3
    # Thumb tucked
    if not states["thumb"]:
        score += 0.2

    return min(score, 1.0)


def check_K(landmarks):
    """ASL 'K': Index and middle extended in V, thumb between them."""
    lm = landmarks
    states = get_finger_states(lm)

    score = 0.0
    # Index and middle extended
    if states["index"] and states["middle"]:
        score += 0.3
    # Ring and pinky curled
    if not states["ring"] and not states["pinky"]:
        score += 0.3
    # Thumb between index and middle (thumb tip near middle of V)
    if states["thumb"]:
        score += 0.2
    # V-shape: index and middle tips spread apart
    v_spread = _distance_2d(lm[INDEX_TIP], lm[MIDDLE_TIP])
    if v_spread > 0.05:
        score += 0.2

    return min(score, 1.0)


def check_L(landmarks):
    """ASL 'L': Index finger up, thumb out, forming L-shape."""
    lm = landmarks
    states = get_finger_states(lm)

    score = 0.0
    # Index extended upward
    if states["index"]:
        score += 0.3
    # Thumb extended outward
    if states["thumb"]:
        score += 0.3
    # Middle, ring, pinky curled
    if not states["middle"] and not states["ring"] and not states["pinky"]:
        score += 0.2
    # L-shape: angle between index (vertical) and thumb (horizontal)
    thumb_horizontal = abs(lm[THUMB_TIP][0] - lm[THUMB_CMC][0])
    index_vertical = abs(lm[INDEX_TIP][1] - lm[INDEX_MCP][1])
    if thumb_horizontal > 0.05 and index_vertical > 0.05:
        score += 0.2

    return min(score, 1.0)


def check_M(landmarks):
    """ASL 'M': Three fingers (index, middle, ring) over thumb, all curled down."""
    lm = landmarks
    states = get_finger_states(lm)
    curl = get_finger_curl(lm)

    score = 0.0
    # All fingers curled
    if not states["index"] and not states["middle"] and not states["ring"]:
        score += 0.4
    # Pinky curled too
    if not states["pinky"]:
        score += 0.1
    # Thumb tucked under fingers
    if lm[THUMB_TIP][1] > lm[INDEX_MCP][1]:
        score += 0.25
    # Three fingertips close together and below MCPs
    tips_close = (_distance_2d(lm[INDEX_TIP], lm[MIDDLE_TIP]) < 0.06 and
                  _distance_2d(lm[MIDDLE_TIP], lm[RING_TIP]) < 0.06)
    if tips_close:
        score += 0.25

    return min(score, 1.0)


def check_N(landmarks):
    """ASL 'N': Two fingers (index, middle) over thumb, curled."""
    lm = landmarks
    states = get_finger_states(lm)

    score = 0.0
    # Index and middle curled
    if not states["index"] and not states["middle"]:
        score += 0.4
    # Ring and pinky curled
    if not states["ring"] and not states["pinky"]:
        score += 0.2
    # Thumb tucked under two fingers
    if lm[THUMB_TIP][1] > lm[MIDDLE_MCP][1]:
        score += 0.2
    # Index and middle tips close together
    tips_close = _distance_2d(lm[INDEX_TIP], lm[MIDDLE_TIP]) < 0.06
    if tips_close:
        score += 0.2

    return min(score, 1.0)


def check_O(landmarks):
    """ASL 'O': All fingertips touching thumb forming O shape."""
    lm = landmarks

    score = 0.0
    # All fingertips close to thumb tip
    for tip in [INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]:
        dist = _distance_2d(lm[THUMB_TIP], lm[tip])
        if dist < 0.08:
            score += 0.2

    # Fingers curved inward (partial curl)
    curl = get_finger_curl(lm)
    if all(curl[f] > 0.15 for f in ["index", "middle", "ring", "pinky"]):
        score += 0.2

    return min(score, 1.0)


def check_P(landmarks):
    """ASL 'P': Like K but pointing downward."""
    lm = landmarks
    states = get_finger_states(lm)

    score = 0.0
    # Index pointing down
    if lm[INDEX_TIP][1] > lm[INDEX_MCP][1]:
        score += 0.3
    # Middle finger extended downward
    if lm[MIDDLE_TIP][1] > lm[MIDDLE_MCP][1]:
        score += 0.2
    # Ring and pinky curled
    if not states["ring"] and not states["pinky"]:
        score += 0.25
    # Thumb out
    if states["thumb"]:
        score += 0.25

    return min(score, 1.0)


def check_Q(landmarks):
    """ASL 'Q': Like G but pointing downward — thumb and index down."""
    lm = landmarks
    states = get_finger_states(lm)

    score = 0.0
    # Index pointing down
    if lm[INDEX_TIP][1] > lm[INDEX_MCP][1]:
        score += 0.3
    # Thumb pointing down
    if lm[THUMB_TIP][1] > lm[THUMB_MCP][1]:
        score += 0.3
    # Middle, ring, pinky curled
    if not states["middle"] and not states["ring"] and not states["pinky"]:
        score += 0.4

    return min(score, 1.0)


def check_R(landmarks):
    """ASL 'R': Index and middle crossed (extended upward)."""
    lm = landmarks
    states = get_finger_states(lm)

    score = 0.0
    # Index and middle extended
    if states["index"] and states["middle"]:
        score += 0.4
    # Ring and pinky curled
    if not states["ring"] and not states["pinky"]:
        score += 0.2
    # Fingers crossed (index tip x crosses over middle tip x)
    index_x = lm[INDEX_TIP][0]
    middle_x = lm[MIDDLE_TIP][0]
    index_mcp_x = lm[INDEX_MCP][0]
    middle_mcp_x = lm[MIDDLE_MCP][0]
    # Check if tips are closer or crossed compared to base
    tips_close = _distance_2d(lm[INDEX_TIP], lm[MIDDLE_TIP]) < 0.04
    if tips_close:
        score += 0.4

    return min(score, 1.0)


def check_S(landmarks):
    """ASL 'S': Fist with thumb over curled fingers."""
    lm = landmarks
    states = get_finger_states(lm)
    curl = get_finger_curl(lm)

    score = 0.0
    # All fingers curled
    if not states["index"] and not states["middle"] and not states["ring"] and not states["pinky"]:
        score += 0.4
    # Thumb over fingers (not alongside like A)
    if not states["thumb"]:
        score += 0.2
    # Thumb tip in front of curled fingers
    if lm[THUMB_TIP][1] < lm[INDEX_PIP][1]:
        score += 0.2
    # Tight fist
    if all(curl[f] > 0.4 for f in ["index", "middle", "ring", "pinky"]):
        score += 0.2

    return min(score, 1.0)


def check_T(landmarks):
    """ASL 'T': Thumb inserted between index and middle (fist)."""
    lm = landmarks
    states = get_finger_states(lm)

    score = 0.0
    # All fingers curled
    if not states["index"] and not states["middle"] and not states["ring"] and not states["pinky"]:
        score += 0.4
    # Thumb positioned between index and middle
    thumb_x = lm[THUMB_TIP][0]
    index_x = lm[INDEX_MCP][0]
    middle_x = lm[MIDDLE_MCP][0]
    if min(index_x, middle_x) <= thumb_x <= max(index_x, middle_x):
        score += 0.3
    # Thumb tip visible (not hidden behind fist)
    if lm[THUMB_TIP][1] < lm[INDEX_PIP][1]:
        score += 0.3

    return min(score, 1.0)


def check_U(landmarks):
    """ASL 'U': Index and middle extended together upward, others curled."""
    lm = landmarks
    states = get_finger_states(lm)

    score = 0.0
    # Index and middle extended upward
    if states["index"] and states["middle"]:
        score += 0.4
    # Ring and pinky curled
    if not states["ring"] and not states["pinky"]:
        score += 0.3
    # Fingers together (close, not spread like V)
    spread = _distance_2d(lm[INDEX_TIP], lm[MIDDLE_TIP])
    if spread < 0.05:
        score += 0.3

    return min(score, 1.0)


def check_V(landmarks):
    """ASL 'V': Index and middle extended in V-shape (peace sign)."""
    lm = landmarks
    states = get_finger_states(lm)

    score = 0.0
    # Index and middle extended
    if states["index"] and states["middle"]:
        score += 0.4
    # Ring and pinky curled
    if not states["ring"] and not states["pinky"]:
        score += 0.3
    # V-shape: fingers spread apart
    spread = _distance_2d(lm[INDEX_TIP], lm[MIDDLE_TIP])
    if spread > 0.06:
        score += 0.3

    return min(score, 1.0)


def check_W(landmarks):
    """ASL 'W': Index, middle, ring extended and spread, pinky curled."""
    lm = landmarks
    states = get_finger_states(lm)

    score = 0.0
    # Three fingers extended
    if states["index"] and states["middle"] and states["ring"]:
        score += 0.4
    # Pinky curled
    if not states["pinky"]:
        score += 0.3
    # Fingers spread
    spread1 = _distance_2d(lm[INDEX_TIP], lm[MIDDLE_TIP])
    spread2 = _distance_2d(lm[MIDDLE_TIP], lm[RING_TIP])
    if spread1 > 0.04 and spread2 > 0.04:
        score += 0.3

    return min(score, 1.0)


def check_X(landmarks):
    """ASL 'X': Index finger hooked (bent at DIP), others curled."""
    lm = landmarks
    states = get_finger_states(lm)

    score = 0.0
    # Middle, ring, pinky curled
    if not states["middle"] and not states["ring"] and not states["pinky"]:
        score += 0.3
    # Index partially extended (PIP above MCP) but tip curved down
    if lm[INDEX_PIP][1] < lm[INDEX_MCP][1]:  # PIP raised
        score += 0.2
    if lm[INDEX_TIP][1] > lm[INDEX_DIP][1]:  # Tip hooked down
        score += 0.3
    # Thumb tucked
    if not states["thumb"]:
        score += 0.2

    return min(score, 1.0)


def check_Y(landmarks):
    """ASL 'Y': Thumb and pinky extended, others curled (shaka)."""
    lm = landmarks
    states = get_finger_states(lm)

    score = 0.0
    # Thumb and pinky extended
    if states["thumb"] and states["pinky"]:
        score += 0.5
    # Index, middle, ring curled
    if not states["index"] and not states["middle"] and not states["ring"]:
        score += 0.5

    return min(score, 1.0)


# ──────────────────────────────────────────────────────────────
# GESTURE REGISTRY
# ──────────────────────────────────────────────────────────────

ASL_GESTURES = {
    "A": check_A,
    "B": check_B,
    "C": check_C,
    "D": check_D,
    "E": check_E,
    "F": check_F,
    "G": check_G,
    "H": check_H,
    "I": check_I,
    # "J": motion-required (not supported in single-frame recognition)
    "K": check_K,
    "L": check_L,
    "M": check_M,
    "N": check_N,
    "O": check_O,
    "P": check_P,
    "Q": check_Q,
    "R": check_R,
    "S": check_S,
    "T": check_T,
    "U": check_U,
    "V": check_V,
    "W": check_W,
    "X": check_X,
    "Y": check_Y,
    # "Z": motion-required (not supported in single-frame recognition)
}
