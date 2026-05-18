#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import asyncio
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Colors:
    """ANSI color codes for terminal output"""
    # Reset
    RESET = '\033[0m'
    
    # Regular colors
    BLACK = '\033[0;30m'
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[0;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[0;37m'
    
    # Bold colors
    BOLD_BLACK = '\033[1;30m'
    BOLD_RED = '\033[1;31m'
    BOLD_GREEN = '\033[1;32m'
    BOLD_YELLOW = '\033[1;33m'
    BOLD_BLUE = '\033[1;34m'
    BOLD_PURPLE = '\033[1;35m'
    BOLD_CYAN = '\033[1;36m'
    BOLD_WHITE = '\033[1;37m'
    
    # Background colors
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_PURPLE = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'
    
    @staticmethod
    def bold(text: str) -> str:
        """Make text bold"""
        return f'\033[1m{text}{Colors.RESET}'
    
    @staticmethod
    def underline(text: str) -> str:
        """Underline text"""
        return f'\033[4m{text}{Colors.RESET}'


class SimpleCLI:
    def __init__(self):
        self.args = None
        self.messages = []

    def parse_args(self):
        parser = argparse.ArgumentParser(prog='haoner', description='Haoner AI Agent')
        subparsers = parser.add_subparsers(dest='command', help='Commands')
        chat_parser = subparsers.add_parser('chat', help='Start chat')
        chat_parser.add_argument('-q', '--query', type=str, help='Single query')
        chat_parser.add_argument('--list-tools', action='store_true', help='List tools')
        chat_parser.add_argument('--toolsets', type=str, nargs='+', default=['terminal'])
        subparsers.add_parser('version')
        self.args = parser.parse_args()
        if self.args.command is None:
            self.args.command = 'chat'
            self.args.query = None
            self.args.list_tools = False
            self.args.toolsets = ['terminal']

    def print_banner(self):
        """Print colorful banner"""
        print()
        print(Colors.BOLD_CYAN + '╔════════════════════════════════════════════════════════════════╗' + Colors.RESET)
        print(Colors.BOLD_CYAN + '║' + Colors.RESET + '                      ' + Colors.BOLD_PURPLE + 'HAONER' + Colors.RESET + ' - AI Agent CLI                      ' + Colors.BOLD_CYAN + '║' + Colors.RESET)
        print(Colors.BOLD_CYAN + '╚════════════════════════════════════════════════════════════════╝' + Colors.RESET)
        print()

    def get_tools(self):
        from tools.model_tools import get_tool_definitions
        return get_tool_definitions()

    def print_tools(self):
        """Print available tools with colors"""
        tools = self.get_tools()
        print(Colors.BOLD_BLUE + '╔════════════════════════════════════════════════════════════════╗' + Colors.RESET)
        print(Colors.BOLD_BLUE + '║' + Colors.RESET + '                      ' + Colors.BOLD_YELLOW + 'Available Tools' + Colors.RESET + '                      ' + Colors.BOLD_BLUE + '║' + Colors.RESET)
        print(Colors.BOLD_BLUE + '╚════════════════════════════════════════════════════════════════╝' + Colors.RESET)
        print()
        
        for i, tool in enumerate(tools, 1):
            func = tool['function']
            name = func['name']
            desc = func.get('description', '')
            
            print(Colors.BOLD_GREEN + f' [{i}] ' + Colors.BOLD_WHITE + name + Colors.RESET)
            if desc:
                print(Colors.BLACK + '    └─ ' + desc + Colors.RESET)
            print()

    async def run_agent(self, user_input):
        from agent.agent_loop import create_agent_loop
        from agent.prompt_builder import build_prompt
        from tools.model_tools import get_tool_definitions
        agent_loop = create_agent_loop(toolsets=self.args.toolsets)
        tools = get_tool_definitions(self.args.toolsets)
        messages = build_prompt(user_message=user_input, tools=tools, history=self.messages)
        result = await agent_loop.run(messages)
        self.messages = result.messages
        for msg in reversed(result.messages):
            if msg.get('role') == 'assistant':
                return msg.get('content', '')
        return 'No response'

    async def run_interactive(self):
        self.print_banner()
        print(Colors.YELLOW + '💡 Type "exit" or "quit" to quit' + Colors.RESET)
        print()
        
        while True:
            try:
                user_input = input(Colors.BOLD_GREEN + 'You' + Colors.RESET + Colors.GREEN + ': ' + Colors.RESET)
            except EOFError:
                break
            
            if user_input.strip().lower() in ['exit', 'quit']:
                print()
                print(Colors.BOLD_BLUE + '👋 Goodbye!' + Colors.RESET)
                break
            
            if not user_input.strip():
                continue
            
            print(Colors.YELLOW + '🔄 Thinking...' + Colors.RESET)
            response = await self.run_agent(user_input)
            
            print()
            print(Colors.BOLD_PURPLE + 'Haoner' + Colors.RESET + Colors.PURPLE + ': ' + Colors.RESET + response)
            print()

    async def run_query(self, query):
        print(Colors.BOLD_BLUE + '╔════════════════════════════════════════════════════════════════╗' + Colors.RESET)
        print(Colors.BOLD_BLUE + '║' + Colors.RESET + '                         ' + Colors.BOLD_YELLOW + 'Query' + Colors.RESET + '                          ' + Colors.BOLD_BLUE + '║' + Colors.RESET)
        print(Colors.BOLD_BLUE + '╚════════════════════════════════════════════════════════════════╝' + Colors.RESET)
        print()
        print(Colors.WHITE + query + Colors.RESET)
        print()
        
        print(Colors.YELLOW + '🔄 Processing...' + Colors.RESET)
        response = await self.run_agent(query)
        
        print()
        print(Colors.BOLD_BLUE + '╔════════════════════════════════════════════════════════════════╗' + Colors.RESET)
        print(Colors.BOLD_BLUE + '║' + Colors.RESET + '                       ' + Colors.BOLD_GREEN + 'Response' + Colors.RESET + '                       ' + Colors.BOLD_BLUE + '║' + Colors.RESET)
        print(Colors.BOLD_BLUE + '╚════════════════════════════════════════════════════════════════╝' + Colors.RESET)
        print()
        print(Colors.PURPLE + response + Colors.RESET)
        print()

    async def run(self):
        self.parse_args()
        if self.args.command == 'version':
            print(Colors.BOLD_CYAN + 'Haoner CLI v1.0.0' + Colors.RESET)
            print(Colors.BLACK + 'AI Agent powered by Anthropic API' + Colors.RESET)
        elif self.args.command == 'chat':
            if self.args.list_tools:
                self.print_tools()
            elif self.args.query:
                await self.run_query(self.args.query)
            else:
                await self.run_interactive()


def main():
    cli = SimpleCLI()
    try:
        asyncio.run(cli.run())
    except KeyboardInterrupt:
        print()
        print(Colors.BOLD_RED + '⚠️  Interrupted' + Colors.RESET)
        print(Colors.BOLD_BLUE + '👋 Goodbye!' + Colors.RESET)
        sys.exit(0)


if __name__ == '__main__':
    main()
