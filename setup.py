from setuptools import find_packages, setup


setup(name='fsm',
      version='0.9',
      description='Finite State Machine designed with simplicity in mind.',
      url='',
      author='Aleksey Izmailov',
      author_email='izmailoff@gmail.com',
      license='MIT',
      packages=find_packages(),
      test_suite='nose.collector',
      install_requires=['colorlog==6.7.0', 'psycopg2-binary==2.9.9', 'sqlalchemy==2.0.9'],
      tests_require=['nose', 'pytest', 'mock', 'nosexcover', 'mypy', 'mongomock', 'mongoengine'],
      zip_safe=False)
