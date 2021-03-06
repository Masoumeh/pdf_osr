from imutils.object_detection import non_max_suppression
import numpy as np
import argparse,pytesseract
import time
import cv2

# load the input image and grab the image dimensions
image = cv2.imread('outputs/Bosworth3.jpg')
orig = image.copy()
(H, W) = image.shape[:2]
print(W,H)
# set the new width and height and then determine the ratio in change
# for both the width and height
(newW, newH) = (1760, 2240)
rW = W / float(newW)
rH = H / float(newH)
# resize the image and grab the new image dimensions
image = cv2.resize(image, (newW, newH))
(H, W) = image.shape[:2]

layerNames = [
	"feature_fusion/Conv_7/Sigmoid",
	"feature_fusion/concat_3"]

print("[INFO] loading EAST text detector...")
net = cv2.dnn.readNet('frozen_east_text_detection.pb')
# construct a blob from the image and then perform a forward pass of
# the model to obtain the two output layer sets
# blob = cv2.dnn.blobFromImage(image, 1.0, (W, H),
# 	(123.68, 116.78, 103.94), swapRB=True, crop=False)
# blob = cv2.dnn.blobFromImage(image, 1.0, (W, H),
# 	(224, 116.78, 103.94), swapRB=True, crop=False)
blob = cv2.dnn.blobFromImage(image, 1, (1760, 2240), (123.68, 116.78, 103.94), swapRB=True, crop=False)
# print("First Blob: {}".format(blob.shape), swapRB=True, crop=False)
start = time.time()
net.setInput(blob)
(scores, geometry) = net.forward(layerNames)
end = time.time()
# show timing information on text prediction
print("[INFO] text detection took {:.6f} seconds".format(end - start))

# grab the number of rows and columns from the scores volume, then
# initialize our set of bounding box rectangles and corresponding
# confidence scores
(numRows, numCols) = scores.shape[2:4]
rects = []
confidences = []
# loop over the number of rows
for y in range(0, numRows):
	# extract the scores (probabilities), followed by the geometrical
	# data used to derive potential bounding box coordinates that
	# surround text
	scoresData = scores[0, 0, y]
	xData0 = geometry[0, 0, y]
	xData1 = geometry[0, 1, y]
	xData2 = geometry[0, 2, y]
	xData3 = geometry[0, 3, y]
	anglesData = geometry[0, 4, y]

	# loop over the number of columns
	for x in range(0, numCols):
		# if our score does not have sufficient probability, ignore it
		if scoresData[x] < 0.5:
			continue
		# compute the offset factor as our resulting feature maps will
		# be 4x smaller than the input image
		(offsetX, offsetY) = (x * 4.0, y * 4.0)
		# extract the rotation angle for the prediction and then
		# compute the sin and cosine
		angle = anglesData[x]
		cos = np.cos(angle)
		sin = np.sin(angle)
		# use the geometry volume to derive the width and height of
		# the bounding box
		h = xData0[x] + xData2[x]
		w = xData1[x] + xData3[x]
		# compute both the starting and ending (x, y)-coordinates for
		# the text prediction bounding box
		endX = int(offsetX + (cos * xData1[x]) + (sin * xData2[x]))
		endY = int(offsetY - (sin * xData1[x]) + (cos * xData2[x]))
		startX = int(endX - w)
		startY = int(endY - h)
		# add the bounding box coordinates and probability score to
		# our respective lists
		rects.append((startX, startY, endX, endY))
		confidences.append(scoresData[x])

# apply non-maxima suppression to suppress weak, overlapping bounding
# boxes
boxes = non_max_suppression(np.array(rects), probs=confidences)
results = []
# loop over the bounding boxes
for (startX, startY, endX, endY) in boxes:
	# scale the bounding box coordinates based on the respective
	# ratios
	startX = int(startX * rW)
	startY = int(startY * rH)
	endX = int(endX * rW)
	endY = int(endY * rH)
	# draw the bounding box on the image
	cv2.rectangle(orig, (startX, startY), (endX, endY), (0, 255, 0), 2)
	roi = orig[startY:endY, startX:endX]
	config = ("-l eng --oem 3 --psm 6")
	text = pytesseract.image_to_string(roi, config=config)
	# results.append(text)
	results.append(((startX, startY, endX, endY), text))

# orig.save("test.jpg")
# show the output image
cv2.imshow("Text Detection", orig)
cv2.waitKey(0)

# sort the results bounding box coordinates from top to bottom
# results = sorted(results, key=lambda r:r[0][1])
print(results)
cnt_crop = 0
# loop over the results
for ((startX, startY, endX, endY), text) in results:
	# display the text OCR'd by Tesseract
	print("OCR TEXT")
	print("========")
	print("{}\n".format(text))
	# strip out non-ASCII text so we can draw the text on the image
	# using OpenCV, then draw the text and a bounding box surrounding
	# the text region of the input image
	text = "".join([c if ord(c) < 128 else "" for c in text]).strip()
	output = orig.copy()
	cv2.rectangle(output, (startX, startY), (endX, endY),
		(0, 0, 255), 2)
	cv2.putText(output, text, (startX, startY - 20),
		cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)

	crop_img = output[startY:endY, startX:endX]
	cv2.imwrite("outputs/Bos_cropped" + str(cnt_crop) + ".png", crop_img)
	# cv2.waitKey(0)
	# show the output image
cv2.imshow("Text Detection", output)
cv2.waitKey(0)