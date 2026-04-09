from yoyo.modules.shared.enums import GuidePlaybackState


def next_playback_state(action: str) -> GuidePlaybackState:
    if action == "trigger":
        return GuidePlaybackState.TRIGGERED
    if action == "play":
        return GuidePlaybackState.PLAYING
    if action == "complete":
        return GuidePlaybackState.PLAYED
    if action == "skip":
        return GuidePlaybackState.SKIPPED
    return GuidePlaybackState.NOT_TRIGGERED
