import sys
from setuptools import setup
setup(
 name = "pedalpii",
 version = "1.0",
 packages = [ 'pedalpII' ],

# pedalpii is primarly intended for raspberrypi* platform and this program really
# relies on RPi.GPIO. But user can use this program on different target in a
# degraded mode.
 install_requires = ['tornado'],

 author="auto3000",
 author_email = "auto3000@users.noreply.github.com",
 description = "Physical (button/LCD) and console interfaces for the pedalpii.",
 license = "GPLv3",
 keywords= "pedalpii",
 url = "https://github.com/auto3000/pedalpii",
)

