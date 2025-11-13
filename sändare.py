from tkinter import *
import config
import json
import threading
from os import _exit


#MORSE_CODE_DICT = {' ': '0', 'e': '1', 'a': '2', 'n': '10', 'r': '11', 't': '12', 's': '20', 'i': '21', 'l': '22', 'd': '100', 'o': '101', 'm': '102', 'k': '110', 'g': '111', 'v': '112', 'h': '120', 'f': '121', 'u': '122', 'p': '200', 'ä': '201', 'b': '202', 'c': '210', 'å': '211', 'ö': '212', 'y': '220', 'j': '221', 'x': '222', 'w': '1000', 'z': '1001', 'q': '1002', 'E': '1010', 'A': '1011', 'N': '1012', 'R': '1020', 'T': '1021', 'S': '1022', 'I': '1100', 'L': '1101', 'D': '1102', 'O': '1110', 'M': '1111', 'K': '1112', 'G': '1120', 'V': '1121', 'H': '1122', 'F': '1200', 'U': '1201', 'P': '1202', 'Ä': '1210', 'B': '1211', 'C': '1212', 'Å': '1220', 'Ö': '1221', 'Y': '1222', 'J': '2000', 'X': '2001', 'W': '2002', 'Z': '2010', 'Q': '2011', '.': '2012', ',': '2020', '!': '2021', '1': '2022', '2': '2100', '3': '2101', '4': '2102', '5': '2110', '6': '2111', '7': '2112', '8': '2120', '9': '2121', '0': '2122', 'STOP': '2200'}
MORSE_CODE_DICT = config.MORSE_CODE_DICT


PULSE_TIME_SHORT = config.PULSE_TIME_SHORT
SLEEP_TIME_LONG = PULSE_TIME_SHORT * 2
SLEEP_TIME_SHORT = PULSE_TIME_SHORT / 2

morse_index = 0
stop = False
kill_program = False

"""Example of analog output voltage generation.

This example demonstrates how to output a continuous periodic
waveform using an internal sample clock.
"""

from typing import Tuple
from time import sleep

import numpy as np
import numpy.typing

import nidaqmx
from nidaqmx.constants import AcquisitionType


def generate_square_wave(
    frequency: float,
    amplitude: float,
    sampling_rate: float,
    number_of_samples: int,
    phase_in: float = 0.0,
) -> Tuple[np.ndarray, float]:
    """Generates a square wave with a specified phase.

    Args:
        frequency: Specifies the frequency of the square wave.
        amplitude: Specifies the amplitude of the square wave.
        sampling_rate: Specifies the sampling rate of the square wave.
        number_of_samples: Specifies the number of samples to generate.
        phase_in: Specifies the phase of the square wave in radians.

    Returns:
        Indicates a tuple containing the generated data and the phase
        of the square wave after generation.
    """
    duration_time = number_of_samples / sampling_rate
    duration_radians = duration_time * 2 * np.pi
    t = np.linspace(phase_in, phase_in + duration_radians, number_of_samples, endpoint=False)

    # This will generate a square wave: values flip sign at each half period
    square_wave = amplitude * np.sign(np.sin(frequency * t))
    return (square_wave)




def pulse(task, time_on, time_off, actual_sampling_rate, number_of_samples, sampling_rate):
    # part one: send the AC voltage
    task.timing.cfg_samp_clk_timing(sampling_rate, sample_mode=AcquisitionType.CONTINUOUS)
    data = generate_square_wave(
        frequency=50.0,
        amplitude=3.0,
        sampling_rate=actual_sampling_rate,
        number_of_samples=number_of_samples,
    )
    task.write(data)
    task.start()
    sleep(time_on)
    task.stop()

    # part two: rest and send 0 DC voltage (basically just to make sure that it doesn't keep sending +-max)
    task.timing.cfg_samp_clk_timing(50, sample_mode=AcquisitionType.CONTINUOUS)
    data = [0, 0]
    task.write(data)
    task.start()
    sleep(time_off)
    task.stop()

def send_pulses(morse):
    global morse_index
    global stop
    morse_index = 0

    """Continuously generates a square wave."""
    with nidaqmx.Task() as task:
        sampling_rate = 5000.0
        number_of_samples = 5000
        try:
            task.ao_channels.add_ao_voltage_chan("Dev1/ao0")
        except Exception as e:
            error_popup(e)
            return
        #task.timing.cfg_samp_clk_timing(sampling_rate, sample_mode=AcquisitionType.CONTINUOUS)

        actual_sampling_rate = task.timing.samp_clk_rate
        #print(f"Actual sampling rate: {actual_sampling_rate:g} S/s")



        print(morse)
        for i in range(len(morse)):
            #print(i)
            if (i != 0 and morse[i - 1] == MORSE_CODE_DICT["STOP"]):
                break
            character = morse[i]
            for symbol in character:
                pulse(task, (int(symbol) + 1) * PULSE_TIME_SHORT, SLEEP_TIME_SHORT, actual_sampling_rate, number_of_samples, sampling_rate)
                
            morse_index += 1
            if stop and morse_index != len(morse) - 1:
                morse[morse_index] = MORSE_CODE_DICT["STOP"]
            sleep(SLEEP_TIME_LONG)



        pulse(task, PULSE_TIME_SHORT, SLEEP_TIME_SHORT, actual_sampling_rate, number_of_samples, sampling_rate)
        task.stop()



def hämta():
    #print("Hämtning startad")
    with open("output.txt", 'r', encoding='utf8') as f:
        imported_text = f.read()
        print(imported_text)
        #hämtadData.config(text=imported_text)
    f.close()
    #print("Hämtning klar")
    return

def skicka():
    global stop
    global kill_program
    skickaBtn.config(state="disabled")
    #print('Data som skickas:' + text)
    #print("data skickad")
    morse = []

    for i in text_entry.get("1.0", "end-1c"):
        if i in MORSE_CODE_DICT.keys():
            morse.append(MORSE_CODE_DICT[i])
        else:
            morse.append(format(ord(i), '08b'))

    #morse.insert(0, MORSE_CODE_DICT["START"])
    morse.append(MORSE_CODE_DICT["STOP"])
    #print(morse)

    #thread = threading.Thread(target=send_pulses(morse))
    #thread.start()
    send_pulses(morse)
    if not kill_program:
        skickaBtn.config(state="normal")
        stop_button.config(state="disabled")
        stop = False
    #thread.join()
    #sleep(1)
    #hämta()
    return

def view_history():
    history_window = Toplevel()
    history_window.title = "Historik"

    history_text = Text(history_window)
    history_text.grid(row=0, column=0)

    history_content = ""
    history_imported = ""

    with open("history.json", "r") as f:
        history_imported = json.load(f)
    f.close()

    for message in history_imported:
        history_content += message["timestamp"]
        history_content += "\n"
        history_content += message["message"]
        history_content += "\n\n"

    #print(history_content)
    history_text.insert("1.0", history_content)
    history_text.config(state="disabled")


def error_popup(text):
  error_window = Toplevel()

  error_text = Text(error_window, height=5)
  error_text.insert("1.0", "Någonting gick fel. Är A/D-omvandlaren ikopplad?")
  error_text.config(state="disabled")

  technical_text = Text(error_window)
  technical_text.insert("1.0", "Tekniska detaljer:\n\n")
  technical_text.insert("end", text)
  technical_text.config(state="disabled")

  error_text.grid(row=0, column=0)
  technical_text.grid(row=1, column=0)


def stop_sending():
    global morse_index
    global stop
    stop = True

def skickaBtn_logic():
    stop_button.config(state="normal")
    skicka_thread = threading.Thread(target=skicka)
    skicka_thread.start()


master = Tk()

master.title("Sändare")

Label(master, text='Ange meddelande:', anchor="w", justify="left").grid(row=0, columnspan=2)

# create the Text and keep a reference
text_entry = Text(master, width=50, height=15)
text_entry.grid(row=1, columnspan=2)

# pass callables, not results of calls
skickaBtn = Button(master, text='Skicka', width=25, command=skickaBtn_logic)
skickaBtn.grid(row=2, column=0)

stop_button = Button(master, text="Stop", width=25, command=stop_sending)
stop_button.grid(row=2, column=1)
stop_button.config(state="disabled")

#hämtaBtn = Button(master, text='Hämta', width=25, command=hämta)
#hämtaBtn.grid(row=1, column=0)

#hämtadData = Label(master, text='Här kommer nya meddelanden visas')
#hämtadDataRubrik = Label(master, text='Hämtad data:')
#hämtadData.grid(row=4, column=0)
#hämtadDataRubrik.grid(row=3, column=0)
#
#view_history_button = Button(master, text="Visa historik", width=25, command=lambda: view_history())
#view_history_button.grid(row=5, column=0)


#återställBtn = Button(master, text='Återställ', width=25, command=återställ)
#återställBtn.grid(row=2, column=0)

def on_closing():
    master.destroy()
    stop_sending()
    global kill_program
    kill_program = True
    #print(1)
    #sleep(5)
    #print(2)
    #master.destroy()

# TODO: uncomment this line before finished
master.protocol("WM_DELETE_WINDOW", on_closing)
mainloop()