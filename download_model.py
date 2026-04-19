import urllib.request
url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
out = r"E:\NEXUS\assets\hand_landmarker.task"
print("Downloading hand landmarker model...")
urllib.request.urlretrieve(url, out)
print("Done.")
