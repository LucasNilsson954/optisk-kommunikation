import nidaqmx
import nidaqmx.stream_readers
import numpy as np
import config
import json
import datetime
import tkinter as tk
import threading
import json

from nidaqmx.constants import AcquisitionType


def append_output_to_history(text):
  history = ""

  with open("history.json", "r") as f:
    history = json.load(f)
  f.close()

  history.append(
    {
      "timestamp": str(datetime.datetime.now()).split(".")[0],
      "message": text
    }
  )

  with open("history.json", "w") as f:
    json.dump(history, f)
  f.close()

def clear_history():
  with open("history.json", "w") as f:
    json.dump([], f)
  f.close()

samples_per_channel = 100

kill_loop = False
decoded_text = ""

def listen():
  with nidaqmx.Task() as writeTask, nidaqmx.Task() as readTask:
    try:
      readTask.ai_channels.add_ai_voltage_chan("Dev1/ai0")
    except Exception as e:
      error_popup(e)
      return

    reader = nidaqmx.stream_readers.AnalogMultiChannelReader(readTask.in_stream)

    readTask.timing.cfg_samp_clk_timing(1000, sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan=samples_per_channel)
    
    output = np.zeros([1, samples_per_channel])
    readTask.start()
    isOn = False
    time_passed_on = 0
    time_passed_off = 0
    current_morse_letter = ""
    total_resting = 0
    count_resting = 0
    factor = 0

    short_pulse = config.PULSE_TIME_SHORT * 1000


    # REVERSED_MORSE_CODE_DICT = {
    #   '.-': 'A', '-...': 'B', '-.-.': 'C', '-..': 'D', '.': 'E',
    #   '..-.': 'F', '--.': 'G', '....': 'H', '..': 'I', '.---': 'J',
    #   '-.-': 'K', '.-..': 'L', '--': 'M', '-.': 'N', '---': 'O',
    #   '.--.': 'P', '--.-': 'Q', '.-.': 'R', '...': 'S', '-': 'T',
    #   '..-': 'U', '...-': 'V', '.--': 'W', '-..-': 'X', '-.--': 'Y',
    #   '--..': 'Z', '.----': '1', '..---': '2', '...--': '3', '....-': '4',
    #   '.....': '5', '-....': '6', '--...': '7', '---..': '8', '----.': '9',
    #   '-----': '0', '--..--': ',', '.-.-.-': '.', '..--..': '?', '-..-.': '/',
    #   '-....-': '-', '-.--.': '(', '-.--.-': ')', '-...-': ' ', '': ''
    # }

    #REVERSED_MORSE_CODE_DICT = {'0': ' ', '1': 'e', '2': 'a', '10': 'n', '11': 'r', '12': 't', '20': 's', '21': 'i', '22': 'l', '100': 'd', '101': 'o', '102': 'm', '110': 'k', '111': 'g', '112': 'v', '120': 'h', '121': 'f', '122': 'u', '200': 'p', '201': 'ä', '202': 'b', '210': 'c', '211': 'å', '212': 'ö', '220': 'y', '221': 'j', '222': 'x', '1000': 'w', '1001': 'z', '1002': 'q', '1010': 'E', '1011': 'A', '1012': 'N', '1020': 'R', '1021': 'T', '1022': 'S', '1100': 'I', '1101': 'L', '1102': 'D', '1110': 'O', '1111': 'M', '1112': 'K', '1120': 'G', '1121': 'V', '1122': 'H', '1200': 'F', '1201': 'U', '1202': 'P', '1210': 'Ä', '1211': 'B', '1212': 'C', '1220': 'Å', '1221': 'Ö', '1222': 'Y', '2000': 'J', '2001': 'X', '2002': 'W', '2010': 'Z', '2011': 'Q', '2012': '.', '2020': ',', '2021': '!', '2022': '1', '2100': '2', '2101': '3', '2102': '4', '2110': '5', '2111': '6', '2112': '7', '2120': '8', '2121': '9', '2122': '0', '2200': 'STOP', '': ''}
    REVERSED_MORSE_CODE_DICT = config.REVERSED_MORSE_CODE_DICT


    def handle_text(current_morse_letter):
      #print(current_morse_letter)
      #decoded_text += REVERSED_MORSE_CODE_DICT[current_morse_letter]
      #print(decoded_text)
      if current_morse_letter in REVERSED_MORSE_CODE_DICT.keys():
        return REVERSED_MORSE_CODE_DICT[current_morse_letter]

      try:
        return chr(int(current_morse_letter, 2))
      except:
        return "ABORT"
    

    # continue reading forever
    while True:
      global kill_loop
      if kill_loop:
        break
      differences = []
      reader.read_many_sample(data = output, 
                              number_of_samples_per_channel = samples_per_channel)
                  
      #Emiting the data just received as a signal
      #print(output)
      #print(len(output[0]))

      # look through collected data for the most recently collected 100 samples
      for j in range(1, len(output[0])):
        previous_value = output[0][j - 1]
        value = output[0][j]

        difference = value - previous_value
        differences.append(difference)
        #print(len(differences))

        # calculate the average difference in a span of four samples
        if (len(differences) >= 3):
          sum = 0
          for i in range(j - 3, j):
            sum += differences[i]
          average = sum / 4

          
          if count_resting != 0 and total_resting != 0:
            factor = abs(average) / (total_resting / count_resting)
          total_resting += abs(average)
          count_resting += 1
          #print(f"{factor:.9f}", total_resting, count_resting, average)
          #if count_resting < 100:
          #  print(f"{factor:.9f}", total_resting, count_resting, average, total_resting / count_resting)

          #print(average)



          # if the differnce is high or low enough then we know the laser has been
          # switched on or off
          # boolean logic is to prevent it from detecting multiple toggles per toggle
          # magic numbers may have to be changed depending on the use case

          # logic for 1
          #print(average)
          if (average < 0 and factor > 10 and not isOn):
            isOn = True
            # extra logic to detect if a 1 was detected
            # if ((time_passed > 200 and previous_time_passed > 200) or (time_passed < 200 and previous_time_passed > 200)):
            #print("on")
            #print(time_passed)
            #time_passed += 1

            # look at how long the light was turned on/off to detect 0s and 1s
            #previous_time_passed = time_passed
            #print("turned on, lamp was off for: ", time_passed_off)

            if (time_passed_off > ((1.5 * short_pulse - short_pulse * 0.2)) and time_passed_off < ((2 * short_pulse + short_pulse * 1))):
              #print("time off: ", time_passed_off)
              #print("NEW LETTER!!")
              letter = handle_text(current_morse_letter)
              global decoded_text
              global update_latest_message
              if letter == "ABORT":
                update_latest_message("Någonting gick fel. Avbröt insamling av signaler.")
                kill_loop = True
              elif letter == "STOP":
                global getting_text
                getting_text = False
                global idle
                idle()

                update_latest_message(decoded_text.strip())
                #print("\ndu fick meddelandet:\n"+decoded_text.strip())
                #write_output_to_file(decoded_text.strip())
                append_output_to_history(decoded_text.strip())
                decoded_text = ""
                current_morse_letter = ""
                differences.clear()
                output = np.zeros([1, samples_per_channel])
                isOn = False
                time_passed_on = 0
                time_passed_off = 0
                break
              decoded_text += letter
              #print(decoded_text.strip())
              global show_new_text
              show_new_text(decoded_text.strip())
              current_morse_letter = ""
              #time.sleep(0.01)


            time_passed_off = 0
            
          if (isOn):
            time_passed_on += 1
          else:
            time_passed_off += 1

          #print(factor, average)
          #if (time_passed_off > 0):
          #  print(time_passed_off)

          if (average > 0 and factor > 10 and isOn and time_passed_on > 5):
            #print(time_passed_on)
            #print("off")
            isOn = False
            #print("turned off, lamp was on for: ", time_passed_on)

            #if (time_passed_on > ((3 * short_pulse + short_pulse / 8) / factor)):
            #  current_morse_letter += '3'
            if (time_passed_on > 3 * short_pulse - short_pulse * 0.4): # 300
              current_morse_letter += '2'
            elif (time_passed_on < 2 * short_pulse + short_pulse * 0.6 and time_passed_on > 2 * short_pulse - short_pulse * 0.4): # 200
              current_morse_letter += '1'
            elif (time_passed_on < 1 * short_pulse + short_pulse * 0.6 and time_passed_on > 1 * short_pulse - short_pulse * 0.4): # 100
              current_morse_letter += '0'

            time_passed_on = 0


      #Pausing before reading buffer again
      #time.sleep(1)

thread = threading.Thread(target=listen)
thread.start()

master = tk.Tk()
master.title("Mottagare")

# live updates on the message
gathered_text = tk.Text(master, width=50, height=5)
gathered_text.insert("1.0", "Lyssnar")
gathered_text.grid(row=0, columnspan=2)

# the final message received
final_text = tk.Text(master, width=50, height=10)
final_text.insert("1.0", "Här kommer det senaste meddelandet visas")
final_text.config(state="disabled")
final_text.grid(row=1, columnspan=2)


view_history_button = tk.Button(master, text="Visa historik", width=25, command=lambda: view_history())
view_history_button.grid(row=2, column=0)

view_history_button = tk.Button(master, text="Rensa historik", width=25, command=lambda: clear_history())
view_history_button.grid(row=2, column=1)

def error_popup(text):
  error_window = tk.Toplevel()

  error_text = tk.Text(error_window, height=5)
  error_text.insert("1.0", "Någonting gick fel. Är A/D-omvandlaren inkopplad?")
  error_text.config(state="disabled")

  technical_text = tk.Text(error_window)
  technical_text.insert("1.0", "Tekniska detaljer:\n\n")
  technical_text.insert("end", text)
  technical_text.config(state="disabled")

  error_text.grid(row=0, column=0)
  technical_text.grid(row=1, column=0)

def on_closing():
  global kill_loop
  kill_loop = True 
  thread.join()
  master.destroy()

def update_latest_message(text):
  final_text.config(state="normal")
  final_text.delete("1.0", "end")
  final_text.insert("1.0", text)

getting_text = False
def show_new_text(text):
  global getting_text
  getting_text = True
  #print(text)
  gathered_text.config(state="normal")
  gathered_text.delete("1.0", "end")
  gathered_text.insert("1.0", text)
  gathered_text.config(state="disabled")

def idle():
  if getting_text:
    return

  current_text = gathered_text.get("1.0", "end-1c")
  gathered_text.config(state="normal")
  gathered_text.delete("1.0", "end")

  if current_text == "Lyssnar":
    gathered_text.insert("1.0", "Lyssnar.")
  elif current_text == "Lyssnar.":
    gathered_text.insert("1.0", "Lyssnar..")
  elif current_text == "Lyssnar..":
    gathered_text.insert("1.0", "Lyssnar...")
  else:
    gathered_text.insert("1.0", "Lyssnar")

  gathered_text.config(state="disabled")

  master.after(333, idle)

def view_history():
  history_window = tk.Toplevel()
  history_window.title = "Historik"

  history_text = tk.Text(history_window)
  scrollbar = tk.Scrollbar(history_window, command=history_text.yview)
  scrollbar.grid(row=0, column=0, sticky="nse")
  history_text["yscrollcommand"] = scrollbar.set
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

  history_text.insert("1.0", history_content)
  history_text.config(state="disabled")


idle()
master.protocol("WM_DELETE_WINDOW", on_closing)
master.mainloop()
