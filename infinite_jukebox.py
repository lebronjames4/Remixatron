"""infinite_jukebox.py - (c) 2017 - Dave Rensin - dave@rensin.com

An attempt to re-create the amazing Infinite Jukebox (http://www.infinitejuke.com)
created by Paul Lemere of Echo Nest. Uses the Remixatron module to do most of the
work.

"""

import argparse
import curses
import os
import pygame
import sys
import time

from Remixatron import InfiniteJukebox
from pygame import mixer

def process_args():

    """ Process the command line args """

    description = """Creates an infinite remix of an audio file by finding musically similar beats and computing a randomized play path through them. The default choices should be suitable for a variety of musical styles. This work is inspired by the Infinite Jukebox (http://www.infinitejuke.com) project creaeted by Paul Lemere (paul@echonest.com)"""

    epilog = """
    """

    parser = argparse.ArgumentParser(description=description, epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("filename", type=str,
                        help="the name of the audio file to play. Most common audio types should work. (mp3, wav, ogg, etc..)")

    parser.add_argument("-clusters", type=int, default=0,
                        help="set the number of clusters into which we want to bucket the audio. Deafult: 0 (automatically try to find the optimal cluster value.)")

    parser.add_argument("-start", type=int, default=1,
                        help="start on beat N. Deafult: 1")

    return parser.parse_args()

def MyCallback(pct_complete, message):

    """ The callback function that gets status updates. Just prints a low-fi progress bar and reflects
        the status message passed in.

        Example: [######    ] Doing some thing...
    """

    curses.setupterm()
    term_width = curses.tigetnum('cols')

    progress_bar = " [" + "".ljust(int(pct_complete * 10),'#') + "".ljust(10 - int(pct_complete * 10), ' ') + "] "
    log_line =  progress_bar + message

    sys.stdout.write( log_line.ljust(term_width) + '\r' )
    sys.stdout.flush()


def display_playback_progress(v):

    """
        Displays a super low-fi playback progress map

        Example:  .............[16].....................

        The dots are the measures in the song. The *number* is a countdown of how
        many beats until a possible jump. The *location* of the number
        is the currently playing beat.

        Returns the time this function took so we can deduct it from the
        sleep time for the beat
    """

    time_start = time.time()

    curses.setupterm()
    term_width = curses.tigetnum('cols')

    v_idx = max(0, jukebox.play_vector.index(v) - 1)
    beat = jukebox.play_vector[v_idx]['beat']
    min_sequence = jukebox.play_vector[v_idx]['seq_len']
    current_sequence = jukebox.play_vector[v_idx]['seq_pos']

    pct = float(beat) / len(jukebox.beats)
    term_pos = int( pct * term_width )

    prefix = "".ljust( min(term_pos, term_width - 4), '.') + '[' + str(min_sequence - current_sequence).zfill(2) + ']'
    log_line =  prefix + "".ljust(term_width - len(prefix), '.')

    sys.stdout.write( log_line.ljust(term_width) + '\r' )
    sys.stdout.flush()

    time_finish = time.time()

    return time_finish - time_start

def show_verbose_info():
    """Show statistics about the song and the analysis"""

    info = """

    filename: %s
    duration: %f seconds
       beats: %d
       tempo: %f beats per minute
    clusters: %d
  samplerate: %d
    """

    print(info % (os.path.basename(args.filename), jukebox.duration,
                  len(jukebox.beats), jukebox.tempo, jukebox.clusters, jukebox.sample_rate))

if __name__ == "__main__":

    """ Main logic """

    try:

        args = process_args()

        print()

        # do the clustering. Run synchronously. Post status messages to MyCallback()
        jukebox = InfiniteJukebox(filename=args.filename, start_beat=args.start, clusters=args.clusters,
                                  progress_callback=MyCallback, async=False)

        # show more info about what was found
        show_verbose_info()

        # important to make sure the mixer is setup with the
        # same sample rate as the audio. Otherwise the playback will
        # sound too slow/fast/awful

        mixer.init(frequency=jukebox.sample_rate)
        channel = mixer.Channel(0)

        # go through the playback list, start playing each beat, display the progress
        # and wait for the playback to complete. Playback happens on another thread
        # in the pygame library, so we have to wait for the beat's duration.

        for v in jukebox.play_vector:

            beat_to_play = jukebox.beats[ v['beat'] ]

            snd = mixer.Sound(buffer=beat_to_play['buffer'])
            channel.queue(snd)

            how_long_this_took = display_playback_progress(v)

            pygame.time.wait( int( (beat_to_play['duration'] - how_long_this_took) * 1000 ) )

    except KeyboardInterrupt:
        print()
        print('exiting...')
        mixer.quit()
