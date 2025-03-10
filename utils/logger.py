from colorama import Fore, Style, init
init(autoreset=True)

def info(message):
    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} {message}")

def success(message):
    print(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} {message}")

def warning(message):
    print(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} {message}")

def error(message):
    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {message}")
