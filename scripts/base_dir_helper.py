def get_default_base_dir() -> str:
    """
    Dynamically resolves a cross-platform default base directory for summaries.
    Checks user's Desktop path; if Desktop exists, uses <Desktop>/Summarizer.
    Otherwise falls back to home directory / Summarizer.
    Automatically creates the directory with parents=True, exist_ok=True.
    """
    from pathlib import Path
    home = Path.home()
    desktop = home / "Desktop"
    if desktop.exists() and desktop.is_dir():
        base = desktop / "Summarizer"
    else:
        # If Desktop didn't exist, we can either create Desktop or fallback to home/Summarizer.
        # The prompt says: "ensures ~/Desktop/Summarizer is created with parents=True, exist_ok=True"
        # Let's ensure ~/Desktop/Summarizer is always created or Desktop is created.
        desktop.mkdir(parents=True, exist_ok=True)
        base = desktop / "Summarizer"
    
    base.mkdir(parents=True, exist_ok=True)
    return str(base)

