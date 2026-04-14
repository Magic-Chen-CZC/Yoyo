# playback.py 只做一件小事：根据 action 决定新的播放状态。
# 它是一个很典型的“规则文件”，适合在理解主流程后再回来看。
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
