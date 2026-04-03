import sys
from modules.gestures.library import get_finger_states, get_finger_curl, ASL_GESTURES
from tests.test_landmarks import SYNTHETIC_GESTURES

gestures = ['A', 'C', 'E', 'O', 'S']

for letter in gestures:
    lm = SYNTHETIC_GESTURES[letter]()
    states = get_finger_states(lm)
    curl = get_finger_curl(lm)
    
    all_scores = [(n, ASL_GESTURES[n](lm)) for n in ASL_GESTURES]
    all_scores.sort(key=lambda x: -x[1])
    
    print(f'=== {letter} ===')
    print(f'Own score: {ASL_GESTURES[letter](lm)}')
    print(f'Top matches: {all_scores[:3]}')
    print(f'Thumb extended: {states["thumb"]}, index: {states["index"]}, middle: {states["middle"]}')
    print(f'Curl: {curl}')
    
    if letter == 'A':
        print('Why P beats A? P checks if index/middle pointing down (tip.y > mcp.y and thumb extended)')
        print(f'A index tip.y={lm[8][1]} > mcp.y={lm[5][1]}? {lm[8][1] > lm[5][1]}')
        print(f'A middle tip.y={lm[12][1]} > mcp.y={lm[9][1]}? {lm[12][1] > lm[9][1]}')
    elif letter == 'C':
        print('Why A beats C? A checks if all curled and thumb extended.')
        print(f'A score of C lm: {ASL_GESTURES["A"](lm)}')
        print(f'C checks: curl values between 0.15 and 0.7. Actual curl: {curl}.')
    elif letter == 'E':
        print('Why Q beats E? Q checks if index/thumb pointing down (tip.y > mcp.y). E thumb tip y: ', lm[4][1], 'mcp y: ', lm[2][1])
        print(f'E index tip y: {lm[8][1]} > mcp.y: {lm[5][1]}? {lm[8][1] > lm[5][1]}')
    elif letter == 'O':
        print('O checks for thumb not extended, but A/N also match?')
    elif letter == 'S':
        print('Why N beats S?')
