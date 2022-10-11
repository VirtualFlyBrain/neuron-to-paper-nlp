from setuptools import setup, find_packages

setup(
    name='neuron-to-paper-nlp',
    version='1.0.0',
    description='A tool for neuron entity linking in the VFB related publications.',
    url='https://github.com/VirtualFlyBrain/neuron-to-paper-nlp',

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Virtual Fly Brain',
        'License :: Apache License Version 2.0',
        'Programming Language :: Python :: 3.8',
    ],

    keywords='entity_linking, neuron_linking, neuron_nlp, vfb_linking',

    packages=find_packages(),

    install_requires=['scispacy', 'rdflib', 'pandas', 'gensim', 'numpy'],
)
