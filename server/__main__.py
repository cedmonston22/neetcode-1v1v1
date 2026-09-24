import uvicorn

from server.main import PORT, lan_ip


def main() -> None:
    print(f"\n  NeetCode 1v1v1 is running. Share this with your roommates:\n\n    http://{lan_ip()}:{PORT}\n")
    uvicorn.run("server.main:app", host="0.0.0.0", port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
