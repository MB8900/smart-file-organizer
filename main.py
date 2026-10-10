"""Smart File Organizer — entry point."""


def main() -> None:
    from ui.app import App
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
