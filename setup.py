from distutils.core import setup
setup(name='grizz',
      version='0.1',
      packages=['markdown'],
      requires=['watchdog'],
      py_modules=['grizz'],
      scripts=['grizz'],
      )
