import re,psutil as ps
import subprocess
from math import pow


def _dmidecode_memory_lines():
    try:
        result = subprocess.run(["dmidecode", "-t", "memory"], check=False, capture_output=True, text=True, timeout=3)
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    return result.stdout.splitlines()


def _memory_hardware_summary():
    lines = _dmidecode_memory_lines()
    speeds = []
    slot_count = 0
    form_factor = None
    for line in lines:
        if ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        lowered = key.lower()
        if lowered == "memory speed" or lowered == "speed":
            slot_count += 1
            match = re.search(r"(\d+)", value)
            if match:
                speeds.append(int(match.group(1)))
        elif lowered == "form factor" and not form_factor:
            form_factor = re.sub(r"\s", "", value)

    speed = f"{min(speeds)} MHz" if speeds else "NA"
    slots = f"{len(speeds)} of {slot_count}" if slot_count else "NA"
    return speed, slots, form_factor or "NA"


def _hardware_corrupted_memory():
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as meminfo:
            for line in meminfo:
                if line.lower().startswith("hardwarecorrupted"):
                    return re.sub(r"\s", "", line.split(":", 1)[1])
    except OSError:
        pass
    return "NA"

def memorytabinit(self):
    """
    Initialisation of Memory components.
    """

    # Fetching and assigning widgets from the glade file
    self.memInfoLabel=self.builder.get_object('meminfolabel')
    self.memInUseLabelValue=self.builder.get_object('meminuselabelvalue')
    self.memAvailableLabelValue=self.builder.get_object('memavailablelabelvalue')
    self.memBuffersLabelValue=self.builder.get_object('membufferslabelvalue')
    self.memCachedLabelValue=self.builder.get_object('memcachedlabelvalue')
    self.memSwapLabelValue=self.builder.get_object('memswaplabelvalue')
    self.memSpeedLabelValue=self.builder.get_object('memspeedlabelvalue')
    self.memSlotLabelValue=self.builder.get_object('memslotlabelvalue')
    self.memFormLabelValue=self.builder.get_object('memformlabelvalue')
    self.memCourruptedLabelValue=self.builder.get_object('memreservedlabelvalue')

    # Memory Utilisation Drawing area
    self.memDrawArea1=self.builder.get_object('memdrawarea1')
    self.memUsedArray1=[0]*100   #mem used array

    # Memory Composition Drawing area
    self.memDrawArea2=self.builder.get_object('memdrawarea2')

    # Total Memory
    self.memTotal=round(ps.virtual_memory()[0]/pow(2,30),1)  # in GiBs
    self.memInfoLabel.set_text(f'{self.memTotal}GiB')

    self.usedd,self.memAvailable,self.memFree=0,0,0

    speed, slots, form_factor = _memory_hardware_summary()
    self.memSpeedLabelValue.set_text(speed)
    self.memSlotLabelValue.set_text(slots)
    self.memFormLabelValue.set_text(form_factor)
    self.memCourruptedLabelValue.set_text(_hardware_corrupted_memory())

def memoryTabUpdate(self):
    """
    Function to periodically update Memory statistics.
    """
    # Conversion divider
    gibdivider=pow(2,30)

    # Getting memory information
    memory=ps.virtual_memory()
    self.usedd=round((memory[0]-memory[1])/gibdivider,1)
    self.memAvailable=round(memory[1]/gibdivider,1)
    self.memFree=round(memory[4]/gibdivider,1)
    self.memPercent=memory[2]

    # Setting the information labels
    self.memInUseLabelValue.set_text(f'{self.usedd} GiB')
    self.memAvailableLabelValue.set_text(f'{self.memAvailable} GiB')
    self.memBuffersLabelValue.set_text(f'{round(memory[7]/gibdivider,1)} GiB')
    self.memCachedLabelValue.set_text(f'{round(memory[8]/gibdivider,1)} GiB')

    # Getting and Setting the swap info
    swapmemory=ps.swap_memory()
    self.memSwapLabelValue.set_text(f'{round(swapmemory[1]/gibdivider,1)}/{round(swapmemory[0]/gibdivider,1)} GiB')

    ## for graph update direction 1 new on right 0 new on left
    if self.update_graph_direction:
        self.memUsedArray1.pop(0)
        self.memUsedArray1.append(self.usedd)
    else:
        self.memUsedArray1.pop()
        self.memUsedArray1.insert(0,self.usedd)

    self.memDrawArea1.queue_draw()
    self.memDrawArea2.queue_draw()
    if hasattr(self, 'memSidePaneDrawArea'):
        self.memSidePaneDrawArea.queue_draw()
