"""Library drawings from Tabler Icons (MIT licence, Paweł Kuna): line icons drawn as single pen lines.
Usage: python3 -I gen_tabler.py <tabler outline icon dir> <out.json> [sheet.png]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

ICONS, OUT = sys.argv[1], sys.argv[2]
SHEET = sys.argv[3] if len(sys.argv) > 3 else None

PICKS = {
 'animals': 'bat cat deer dog dragon fish horse pig spider paw butterfly feather',
 'cars': 'car car-suv car-4wd car-crash ambulance firetruck camper caravan steering-wheel car-garage',
 'nature': 'sun sun-high sunrise sunset-2 moon moon-stars cloud cloud-rain cloud-snow cloud-storm cloud-bolt cloud-fog snowflake rainbow tornado wind comet '
           'mountain volcano tree trees plant plant-2 seedling cactus flower clover flame droplets iceberg acorn cherry beach campfire ripple',
 'leaves': 'leaf leaf-2 leaf-maple clover-2 twig',
 'signs': 'alert-triangle alert-octagon traffic-lights traffic-cone road-sign direction-sign sign-left sign-right parking parking-meter fire-hydrant bus-stop '
          'gas-station recycle radioactive biohazard smoking-no wheelchair medical-cross fire-extinguisher door-exit elevator stairs escalator first-aid-kit',
 'emojis': 'mood-happy mood-smile mood-smile-beam mood-smile-dizzy mood-crazy-happy mood-xd mood-wink mood-wink-2 mood-tongue mood-tongue-wink mood-tongue-wink-2 '
           'mood-heart mood-kid mood-boy mood-nerd mood-sing mood-surprised mood-confused mood-puzzled mood-neutral mood-empty mood-unamused mood-annoyed mood-annoyed-2 '
           'mood-nervous mood-sad mood-sad-2 mood-sad-squint mood-sad-dizzy mood-cry mood-angry mood-wrrr mood-sick mood-silence mood-look-up mood-look-down '
           'mood-look-left mood-look-right ghost ghost-2 pumpkin-scary heart hearts heart-broken sparkles star thumb-up thumb-down hand-love-you hand-stop hand-two-fingers',
 'objects': 'scissors key lamp lamp-2 umbrella backpack basket gift hourglass bell bulb candle crown magnet hammer shovel ruler pencil brush palette paperclip clipboard '
            'book books notebook briefcase wallet shopping-bag shopping-cart package armchair rocking-chair bath clock alarm binoculars tools axe needle-thread yarn '
            'christmas-ball confetti award anchor tent lock flashlight puzzle dice-5 chess-knight chess-queen chess-rook chess-king horse-toy treasure-chest teddy-bear',
 'sports': 'ball-american-football ball-baseball ball-basketball ball-bowling ball-football ball-tennis ball-volleyball barbell bow bowling cliff-jumping cricket curling '
           'disc-golf dumbbell exercise-ball golf helmet hula-hoop ice-skating jump-rope karate kayak medal medal-2 olympic-torch ping-pong play-basketball play-football '
           'play-handball play-volleyball pool roller-skating rugby run run-sprint scoreboard scuba-diving scuba-mask skateboarding ski-jumping soccer-field sport-billiard '
           'stretching swimming target-arrow trekking trophy walk waterpolo yoga bike skateboard',
 'clothing': 'shirt shirt-sport jacket hanger sock tie clothes-rack chef-hat eyeglass sunglasses moustache',
 'shoes': 'shoe flip-flops',
 'aircraft': 'plane plane-tilt plane-inflight plane-departure plane-arrival helicopter drone air-balloon zeppelin parachute windsock',
 'army': 'tank submarine medal-2 military-award military-rank shield helmet binoculars compass parachute',
 'technology': 'cpu cpu-2 server router antenna satellite robot atom atom-2 circuit-battery circuit-bulb circuit-capacitor circuit-diode circuit-inductor circuit-motor '
               'circuit-resistor circuit-switch-open plug battery-charging wifi cloud-computing binary-tree network topology-star dna microscope flask bulb gauge settings '
               'brand-github-copilot gizmo',
 'phones': 'device-mobile device-mobile-vibration device-landline-phone phone device-tablet device-laptop device-desktop device-tv device-tv-old device-watch device-speaker '
           'device-gamepad device-gamepad-2 device-floppy device-sd-card device-audio-tape device-cctv device-remote keyboard mouse printer calculator headphones headset '
           'microphone microphone-2 radio camera polaroid vinyl disc earphone-bluetooth remote-control device-projector battery plug-connected device-usb',
 'music': 'music clef clef-staff guitar-pick piano playlist album',
 'scifi': 'ufo alien robot rocket planet satellite meteor comet galaxy jetpack orbit atom-2',
 'food': 'apple avocado baguette banana bread burger cake candy carrot cheese cherry coffee cookie cup egg-fried ice-cream ice-cream-2 lemon lollipop meat melon milk '
         'mushroom pepper pizza salad sausage soup teapot wheat bowl dumpling carambola milkshake mug grape',
 'places': 'building building-castle building-lighthouse building-mosque building-arch building-bridge building-bridge-2 building-skyscraper building-stadium windmill '
           'building-factory building-cottage building-fortress building-pavilion building-monument building-carousel building-circus building-tunnel home buildings torii tower',
 'transport': 'bike bus train tractor truck ship sailboat sailboat-2 speedboat ferry scooter moped motorbike segway unicycle tir forklift crane bulldozer backhoe '
              'aerial-lift trolley sleigh rollercoaster',
}
NAMES = {'ball-american-football': 'American football', 'ball-football': 'Football', 'play-basketball': 'Basketball player', 'play-football': 'Football player',
         'play-handball': 'Handball player', 'play-volleyball': 'Volleyball player', 'sport-billiard': 'Billiard ball', 'run-sprint': 'Sprinter', 'mood-xd': 'Laughing (XD)',
         'mood-wrrr': 'Grumpy', 'tir': 'Lorry', 'device-tv-old': 'Old TV', 'device-landline-phone': 'Landline phone', 'device-audio-tape': 'Cassette tape',
         'device-cctv': 'Security camera', 'device-sd-card': 'Memory card', 'device-floppy': 'Floppy disk', 'device-usb': 'USB stick', 'earphone-bluetooth': 'Earbud',
         'brand-github-copilot': None, 'smoking-no': 'No smoking', 'door-exit': 'Exit door', 'military-rank': 'Rank chevrons', 'military-award': 'Military medal',
         'medal-2': 'Medal with star', 'sunset-2': 'Sunset', 'atom-2': 'Atom', 'cpu-2': 'Processor chip', 'mood-heart': 'In love', 'mood-kid': 'Child smiling',
         'mood-boy': 'Boy smiling', 'mood-crazy-happy': 'Overjoyed', 'mood-smile-beam': 'Beaming', 'mood-smile-dizzy': 'Dizzy smile', 'mood-sad-dizzy': 'Dizzy and sad',
         'mood-empty': 'Speechless', 'mood-look-up': 'Looking up', 'mood-look-down': 'Looking down', 'mood-look-left': 'Looking left', 'mood-look-right': 'Looking right',
         'mood-silence': 'Lips sealed', 'mood-sing': 'Singing', 'clef-staff': 'Treble clef on a staff', 'clef': 'Treble clef', 'circuit-switch-open': 'Switch (circuit symbol)'}

def pretty(n):
    if n in NAMES: return NAMES[n]
    s = n.replace('mood-', '').replace('device-', '').replace('building-', '').replace('circuit-', '').replace('ball-', '')
    s = s.replace('-2', '').replace('-', ' ').strip()
    if n.startswith('circuit-'): s += ' (circuit symbol)'
    if n.startswith('ball-'): s += ' ball'
    return s[:1].upper() + s[1:]

items, missing = [], []
for cat, names in PICKS.items():
    for n in names.split():
        f = f'{ICONS}/{n}.svg'
        if not os.path.exists(f) or NAMES.get(n, '') is None: missing.append(n); continue
        L = svg_lines(f)
        if not L: missing.append(n); continue
        # dots (eyes, the dot of an i…) are zero-length strokes in the icons: draw them as small rings
        out = []
        for P in L:
            xs = [p[0] for p in P]; ys = [p[1] for p in P]
            if max(xs) - min(xs) < 0.3 and max(ys) - min(ys) < 0.3:
                out.append(circle((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, 0.6, n=14))
            else: out.append(P)
        L = out
        it = Item(cat, pretty(n), L, author='Paweł Kuna (Tabler Icons)', source='tabler-icons', license='MIT', title=f'Tabler icon “{n}”')
        it.slug = 't-' + n; items.append(it)
save(items, OUT)
print('missing:', missing)
from collections import Counter
print(Counter(i.cat for i in items))
if SHEET:
    for i in range(0, len(items), 96):
        sheet(items[i:i + 96], SHEET.replace('.png', f'_{i // 96}.png'), cols=12, cell=1.5)
