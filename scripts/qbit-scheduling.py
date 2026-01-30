#!/usr/bin/env python3
"""
qBittorrent Container Scheduler
Manages qBittorrent Docker container on/off schedule with download detection.
"""

import os

# Install docker and qbittorrent-api via pip if not already installed:
os.system("pip install docker qbittorrent-api")

import docker
import qbittorrentapi
import time
import logging
from datetime import datetime, time as dt_time
import sys

# ============================================================================
# CONFIGURATION
# ============================================================================

# Docker container name
CONTAINER_NAME = "binhex-qbittorrentvpn"

# qBittorrent Web UI connection details
QBITTORRENT_HOST = "127.0.0.1"
QBITTORRENT_PORT = 8080
QBITTORRENT_USERNAME = "admin"
QBITTORRENT_PASSWORD = "adminadmin"

# Schedule: when to turn ON (24-hour format)
TURN_ON_TIME = dt_time(2, 0)  # 2 AM

# Schedule: when to turn OFF (24-hour format)
TURN_OFF_TIME = dt_time(6, 0)  # 6 AM

# How often to check download status when waiting (seconds)
CHECK_INTERVAL = 300  # 5 minutes

# Maximum time to wait for downloads to finish before forcing shutdown (seconds)
# Set None to wait indefinitely
MAX_WAIT_TIME = None

# Container startup wait time (seconds)
CONTAINER_START_WAIT = 120  # 2 minutes

# ============================================================================
# Logging Configuration
# ============================================================================

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================


def get_container(docker_client, container_name):
    """Get Docker container by name."""
    try:
        return docker_client.containers.get(container_name)
    except docker.errors.NotFound:
        logger.error(f"Container '{container_name}' not found!")
        return None
    except Exception as e:
        logger.error(f"Error getting container: {e}")
        return None


def is_container_running(container):
    """Check if container is running."""
    try:
        container.reload()
        return container.status == "running"
    except Exception as e:
        logger.error(f"Error checking container status: {e}")
        return False


def start_container(container):
    """Start Docker container."""
    try:
        if is_container_running(container):
            logger.info("Container is already running")
            return True

        logger.info(f"Starting container '{CONTAINER_NAME}'...")
        container.start()
        time.sleep(CONTAINER_START_WAIT)

        if is_container_running(container):
            logger.info("Container started successfully")
            return True
        else:
            logger.error("Container failed to start")
            return False
    except Exception as e:
        logger.error(f"Error starting container: {e}")
        return False


def stop_container(container):
    """Stop Docker container."""
    try:
        if not is_container_running(container):
            logger.info("Container is already stopped")
            return True

        logger.info(f"Stopping container '{CONTAINER_NAME}'...")
        container.stop(timeout=30)

        if not is_container_running(container):
            logger.info("Container stopped successfully")
            return True
        else:
            logger.error("Container failed to stop")
            return False
    except Exception as e:
        logger.error(f"Error stopping container: {e}")
        return False


def get_qbittorrent_client():
    """Create and return qBittorrent API client."""
    try:
        client = qbittorrentapi.Client(
            host=f"{QBITTORRENT_HOST}:{QBITTORRENT_PORT}",
            username=QBITTORRENT_USERNAME,
            password=QBITTORRENT_PASSWORD,
        )
        client.auth_log_in()
        return client
    except qbittorrentapi.LoginFailed:
        logger.error("qBittorrent login failed - check credentials")
        return None
    except Exception as e:
        logger.error(f"Error connecting to qBittorrent: {e}")
        return None


def is_downloading(qbt_client):
    """
    Check if any torrents are actively downloading.
    Returns tuple: (is_downloading, active_count, torrent_names)
    """
    try:
        torrents = qbt_client.torrents_info()
        downloading_torrents = [t for t in torrents if t.state_enum.is_downloading]

        count = len(downloading_torrents)
        names = [t.name for t in downloading_torrents]

        return (count > 0, count, names)
    except Exception as e:
        logger.error(f"Error checking download status: {e}")
        return (False, 0, [])


def is_time_in_range(target_time, current_time, tolerance_minutes=5):
    """
    Check if current time is within tolerance of target time.
    Handles midnight wraparound.
    """
    target_minutes = target_time.hour * 60 + target_time.minute
    current_minutes = current_time.hour * 60 + current_time.minute

    diff = abs(target_minutes - current_minutes)

    # Handle midnight wraparound
    if diff > 720:  # More than 12 hours
        diff = 1440 - diff

    return diff <= tolerance_minutes


def should_be_running(current_time):
    """
    Determine if qBittorrent should be running based on schedule.
    """
    turn_on_minutes = TURN_ON_TIME.hour * 60 + TURN_ON_TIME.minute
    turn_off_minutes = TURN_OFF_TIME.hour * 60 + TURN_OFF_TIME.minute
    current_minutes = current_time.hour * 60 + current_time.minute

    if turn_on_minutes < turn_off_minutes:
        # Same day schedule (e.g., 8 AM to 5 PM)
        return turn_on_minutes <= current_minutes < turn_off_minutes
    else:
        # Overnight schedule (e.g., 6 PM to 2 AM)
        return current_minutes >= turn_on_minutes or current_minutes < turn_off_minutes


def wait_for_downloads_to_finish(qbt_client):
    """
    Wait for all downloads to finish before allowing shutdown.
    Returns True if downloads finished, False if timeout reached.
    """
    start_wait_time = time.time()

    while True:
        is_dl, count, names = is_downloading(qbt_client)

        if not is_dl:
            logger.info("No active downloads - safe to shutdown")
            return True

        elapsed = time.time() - start_wait_time
        logger.info(
            f"Waiting for {count} download(s) to finish... ({elapsed / 60:.1f} min elapsed)"
        )
        for name in names:
            logger.info(f"  - {name}")

        if MAX_WAIT_TIME and elapsed >= MAX_WAIT_TIME:
            logger.warning(
                f"Max wait time ({MAX_WAIT_TIME / 60:.1f} min) reached - forcing shutdown"
            )
            return False

        time.sleep(CHECK_INTERVAL)


# ============================================================================
# Main Scheduler Logic
# ============================================================================


def run_scheduler():
    """Main scheduler loop - runs once per execution."""
    logger.info("=" * 70)
    logger.info("qBittorrent Scheduler Starting")
    logger.info(f"Container: {CONTAINER_NAME}")
    logger.info(
        f"Schedule: ON at {TURN_ON_TIME.strftime('%H:%M')}, OFF at {TURN_OFF_TIME.strftime('%H:%M')}"
    )
    logger.info("=" * 70)

    # Get Docker client and container
    try:
        docker_client = docker.from_env()
    except Exception as e:
        logger.error(f"Failed to connect to Docker: {e}")
        logger.error("Make sure Docker is running and you have permissions")
        return 1

    container = get_container(docker_client, CONTAINER_NAME)
    if not container:
        return 1

    # Get current time and determine what should happen
    now = datetime.now()
    current_time = now.time()

    logger.info(f"Current time: {current_time.strftime('%H:%M:%S')}")

    # Check if it's time to turn ON
    if is_time_in_range(TURN_ON_TIME, current_time):
        logger.info("==> Turn ON time triggered")
        if start_container(container):
            logger.info("Container is now running")
        return 0

    # Check if it's time to turn OFF
    if is_time_in_range(TURN_OFF_TIME, current_time):
        logger.info("==> Turn OFF time triggered")

        # Make sure container is running before checking downloads
        if not is_container_running(container):
            logger.info("Container is already stopped")
            return 0

        # Connect to qBittorrent and check downloads
        qbt_client = get_qbittorrent_client()
        if not qbt_client:
            logger.warning("Cannot connect to qBittorrent - stopping container anyway")
            stop_container(container)
            return 0

        # Check if downloads are active
        is_dl, count, names = is_downloading(qbt_client)

        if is_dl:
            logger.info(f"Found {count} active download(s):")
            for name in names:
                logger.info(f"  - {name}")

            # Wait for downloads to finish
            finished = wait_for_downloads_to_finish(qbt_client)

            if not finished:
                logger.warning(
                    "Downloads did not finish in time - proceeding with shutdown"
                )

        # Stop the container
        if stop_container(container):
            logger.info("Container is now stopped")

        return 0

    # Not time for any action
    should_run = should_be_running(current_time)
    is_running = is_container_running(container)

    logger.info(f"Current state: Container {'running' if is_running else 'stopped'}")
    logger.info(f"Expected state: Should be {'running' if should_run else 'stopped'}")

    # Ensure container state matches schedule
    if should_run and not is_running:
        logger.info("Container should be running but isn't - starting it")
        start_container(container)
    elif not should_run and is_running:
        logger.info("Container is running but shouldn't be - stopping it")
        qbt_client = get_qbittorrent_client()
        if qbt_client:
            wait_for_downloads_to_finish(qbt_client)
        stop_container(container)
    else:
        logger.info("Container state is correct - no action needed")

    return 0


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    try:
        exit_code = run_scheduler()
        logger.info("Scheduler execution completed")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Scheduler interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
