# pedalpII
Physical (button/LCD) and console interfaces for the pedalpII (aka pedalpi v2).

pedalpII is a monolithic script to control the sound effects from input GPIOs of the Raspberry Pi. pedalpII considers a physical pedal with a LCD 16x2 to display current pedalboard effects, a rotation encoder to control pedal effects and a true bypass switch.

The total cost for this hardware is targeted under 150$. The main cost are the Prodipe Studio 22 USB sound card (80$), the Raspberry Pi 2/3 (40$), and the Hammond 1590DD aluminium box (20$). Remaining furnitures are under 10$: one 1602 LCD display, one MF-A04 bakelite knob, two 1/4 mono jack plug audio connector, two 1/4 jack socket connector female panel mount, and one 3PDT switch true bypass.

## Install and run

There are instructions for installing in a Raspbian based Linux environment. The following packages will be required:

    $ sudo apt-get install python-virtualenv python3-pip python3-dev git

Start by cloning the repository:

    $ git clone https://github.com/auto3000/pedalpii 
    $ cd pedalpii

Create a python virtualenv:

    $ virtualenv pedalpi-env
    $ source pedalpi-env/bin/activate

Install python requirements:

    $ pip3 install -r requirements.txt


Before running the script, you need to activate your virtualenv
(if you have just done that during installation, you can skip this step, but you'll need to do this again when you open a new shell)::

    $ source pedalpi-env/bin/activate

Run the script:

    $ ./pedalpII.py

## History
pedalpII is a complete software rebase from pedalpI (aka pedalpi v1) to cooperate with MOD infrastructure (https://github.com/moddevices).

From an hardware point of view, there is no modification. pedalpI/pedalpII are using a single true bypass button, a single rotary encoder button and a 2-line display LCD. The sound DAC/ADC is managed by Prodipe Studio 22. Prodipe Studio 22 is an external USB1 sound card known for compatibility with Raspberry Pi 2. This sound card does support two input and two output. pedalpI/pedalII only handle a single input and a single output.

From a software point of view, pedalpI is relying on the Rakarrack complete audio effect suite (http://rakarrack.sourceforge.net). Rakarrack is normally controlled by an X-window interface but Rakarrack was able to handle commands from MIDI devices. pedalpI is a shrink of the Rakarrack GUI with a small python script that interface the Raspberry PI GPIOs (for button/LCD) to the Rakarrack effect selection by virtual MIDI commands. 

pedalpII relies on MOD infrastructure. MOD did not exist when pedalpI was developed (first half of 2015). However, there are several points of comparison. Rakarrack and MOD both rely on jack infrastructure for low latency audio. Rakarrack and MOD provides a large set of configurable audio effect. The main limitation of Rakarrack is the single thread execution of audio effects. The single core design of Rakarrack is making the execution of some complex effects impossible on a single core of Raspberry Pi.

## Future of pedalpIII

pedalpIII (aka pedalpi v3) is intended to be an hardware rebase from pedalpII. There are two technical paths:
1- replace the costly USB sound card for a cheaper sound card, like Audio Injector (25$) to reach a 100$ budget 
2- add a second audio input and a second audio output from the actual USB sound card
3- both 1 and 2
4- additional buttons or additional physical commands like expression pedal for wahwah
