"""Debug all remaining gesture failures and write to stdout."""
from modules.gestures.library import ASL_GESTURES, get_finger_states
from tests.test_landmarks import SYNTHETIC_GESTURES

for letter in ['A','C','E','O','S','T','U']:
    lm = SYNTHETIC_GESTURES[letter]()
    states = get_finger_states(lm)
    target = ASL_GESTURES[letter](lm)
    all_scores = sorted([(n, ASL_GESTURES[n](lm)) for n in ASL_GESTURES], key=lambda x: -x[1])
    winner = all_scores[0]
    print(f"{letter}: own={target:.2f} winner={winner[0]}({winner[1]:.2f}) thumb={states['thumb']} tip4={lm[4]} ip3={lm[3]}")
