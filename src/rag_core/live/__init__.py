"""Live-listening building blocks: turning a raw microphone stream into
segmented questions (vad_segmenter) and turning segmented questions into
retrieval answers with speculative partial lookups (question_matcher).

Framework-agnostic, same as the rest of rag_core: no microphone library
import lives here. interfaces/live_listener is the thin adapter that owns
the actual audio device.
"""
