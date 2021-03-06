# pedalpII
pedalpi is an affordable but complete computer-based pedalboard for guitar/bass.

This code implements the physical (button/LCD) and console interfaces for the pedalpII (aka pedalpi v2). pedalpII is a monolithic script to control the sound effects from input GPIOs. pedalpII considers a physical pedal with a LCD 16x2 to display current pedalboard effects, a rotation encoder to select pedal effects and a true bypass switch.

The pedalpII comes into two flavors: (1) Raspberry PI and (2) NanoPI Neo Air.

(1) The total cost for Raspberry PI flavor is targeted under 150$. The main cost are the Prodipe Studio 22 USB sound card (80$), the Raspberry Pi 2/3 (40$), and the Hammond 1590DD aluminium box (20$). Remaining furnitures are under 10$: 2GB SDcard, one 1602 LCD display, one MF-A04 bakelite knob, two 1/4 mono jack plug audio connector, two 1/4 jack socket connector female panel mount, and one 3PDT switch true bypass.

(2) The total cost for this competitor is targeted under 60$. The main cost is the NanoPi Neo Air (30$) that includes a onboard eMMC storage and audio sound codec, and the Hammond 1590DD aluminium box (20$). Remaining furnitures are under 10$: one 1602 LCD display, one MF-A04 bakelite knob, two 1/4 mono jack plug audio connector, and one 3PDT switch true bypass.

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

    $ ./python-pedalpII.py

## History
pedalpII is a complete software rebase from pedalpI (aka pedalpi v1) to cooperate with MOD infrastructure (https://github.com/moddevices).

From an hardware point of view, there is no concept modification since pedalpI. pedalpI/pedalpII are using a single true bypass button, a single rotary encoder button and a 2-line display LCD. The sound DAC/ADC is managed by Prodipe Studio 22. Prodipe Studio 22 is an external USB1 sound card known for compatibility with Raspberry Pi 2. This sound card does support two input and two output.

Any single-board-computers (like Raspberry PI) that must support Linux with an external USB sound card can run pedalpII. But recently we made some effort to reduce the cost of the setup with support of cheap Raspberry clones that have builtin sound card. 

From a software point of view, pedalpI is relying on the Rakarrack complete audio effect suite (http://rakarrack.sourceforge.net). Rakarrack is normally controlled by an X-window interface but Rakarrack was able to handle commands from MIDI devices. pedalpI is a shrink of the Rakarrack GUI with a small python script that interface the Raspberry PI GPIOs (for button/LCD) to the Rakarrack effect selection by virtual MIDI commands. 

pedalpII relies on MOD infrastructure. MOD did not exist when pedalpI was developed (first half of 2015). However, there are several points of comparison. Rakarrack and MOD both rely on jack infrastructure for low latency audio. Rakarrack and MOD provides a large set of configurable audio effect. The main limitation of Rakarrack is the single thread execution of audio effects. The single core design of Rakarrack is making the execution of some complex effects impossible on a single core of Raspberry Pi.

## Future of pedalpIII

In the long term, ideas are welcome:
 - Supports stereo pedal effects with a second audio input and/or a second audio output
 - Supports for additional buttons or additional physical commands like expression pedal for wahwah
