# pedalpII
Physical (button/LCD) and console interfaces for the pedalpII (aka pedalpi v2).

## History of pedalpII
pedalpII is a complete software rebase from pedalpI to cooperate with MOD infrastructure.

From hardware point of view, there is no modification. pedalpI/pedalpII are using a single true bypass button, a single rotary encoder button and a 2-line display LCD. The sound DAC/ADC is managed by Prodipe Studio 22. Prodipe Studio 22 is an external USB1 sound card known for compatibility with Raspberry Pi 2. This sound card does support two input and two output. pedalpI/pedalII only handle a single input and a single output.

The total cost for this hardware is targeted under 150$. The main cost are the Prodipe Studio 22 USB sound card (80$), the Raspberry Pi 2/3 (40$), and the aluminium box (15$).

From a software point of view, pedalpI is relying on the Rakarrack complete audio effect suite. Rakarrack is normally controlled by an X-window interface but Rakarrack was able to handle commands from MIDI devices. pedalpI is a shrink of the Rakarrack GUI with a small python script that interface the Raspberry PI GPIOs (for button/LCD) to the Rakarrack effect selection by virtual MIDI commands. 

pedalpII relies on MOD infrastructure. MOD did not exist when pedalpI was developed (first half of 2015). However, there are several points of comparison. Rakarrack and MOD both rely on jack infrastructure for low latency audio. Rakarrack and MOD provides a large set of configurable audio effect. The main limitation of Rakarrack is the single thread execution of audio effect, making the execution of some complex effects impossible on a single core of Raspberry Pi. 

## Future of pedalpIII

pedalpIII is intended to be an hardware rebase from pedalpII. There are two technical paths:
1- replace the costly USB sound card for a cheaper sound card, like Audio Injector (25$) to reach 100$ budget 
2- add a second audio input and a second audio output from the actual USB sound card
3- both 1 and 2



