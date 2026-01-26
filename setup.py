"""
DweepBot Pro - Autonomous AI Agent Framework
Setup configuration for package installation
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements
def read_requirements(filename):
    """Read requirements from file"""
    with open(filename, 'r') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

# Core requirements
install_requires = [
    'anthropic>=0.18.0',
    'openai>=1.0.0',
    'rich>=13.0.0',
    'python-dotenv>=1.0.0',
    'requests>=2.31.0',
    'pydantic>=2.0.0',
]

# Optional dependencies for different features
extras_require = {
    'web': [
        'duckduckgo-search>=4.0.0',
        'beautifulsoup4>=4.12.0',
        'html2text>=2020.1.16',
    ],
    'docs': [
        'PyPDF2>=3.0.0',
        'python-docx>=1.0.0',
        'markdown>=3.5.0',
    ],
    'rag': [
        'chromadb>=0.4.0',
        'sentence-transformers>=2.2.0',
        'faiss-cpu>=1.7.4',
    ],
    'notifications': [
        'slack-sdk>=3.23.0',
        'discord.py>=2.3.0',
    ],
    'dev': [
        'pytest>=7.4.0',
        'pytest-asyncio>=0.21.0',
        'pytest-cov>=4.1.0',
        'black>=23.0.0',
        'flake8>=6.1.0',
        'mypy>=1.6.0',
        'isort>=5.12.0',
    ],
}

# 'all' includes everything except 'dev'
extras_require['all'] = list(set(
    extras_require['web'] + 
    extras_require['docs'] + 
    extras_require['rag'] + 
    extras_require['notifications']
))

setup(
    name='dweepbot',
    version='0.1.0',
    author='DweepBot Team',
    author_email='hello@dweepbot.com',
    description='Production-grade autonomous AI agent framework with DeepSeek integration',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/dweepbot/dweepbot',
    project_urls={
        'Bug Reports': 'https://github.com/dweepbot/dweepbot/issues',
        'Source': 'https://github.com/dweepbot/dweepbot',
        'Documentation': 'https://github.com/dweepbot/dweepbot/tree/main/docs',
    },
    packages=find_packages(exclude=['tests', 'examples', 'docs']),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.10',
    install_requires=install_requires,
    extras_require=extras_require,
    entry_points={
        'console_scripts': [
            'dweepbot=dweepbot.cli:main',
        ],
    },
    include_package_data=True,
    package_data={
        'dweepbot': [
            'config/*.yaml',
            'prompts/*.txt',
        ],
    },
    keywords='ai agent autonomous deepseek llm framework automation',
    zip_safe=False,
)
