from distutils.core import setup

__author__ = 'Jan Růžička'
__email__ = 'jan.ruzicka01@gmail.com'

__version__ = '0.1'

setup(
    name='PyPEG',
    version=__version__,
    description='Simple PEG parser generator.',
    author=__author__,
    author_email=__email__,
    url='github.com/ruza-net/PyPEG',
    download_url='github.com/ruza-net/PyPEG/archive/master.zip',
    packages=['pypeg'],
    modules=['pypeg.pypeg']
)
