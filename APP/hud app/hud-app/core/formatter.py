def format_metrics(payload):
    return (
        f"FPS:{payload['fps']};"
        f"CPU:{payload['cpu']};"
        f"RAM:{payload['ram']};"
        f"DISK:{payload['disk']};"
        f"TIME:{payload['time']};\n"
    )
