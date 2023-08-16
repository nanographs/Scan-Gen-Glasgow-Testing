#pattern_file = open("software/glasgow/applet/video/scan_gen/1-3ML.bmp","rb")
import struct
#import matplotlib.pyplot as plt
import numpy as np

file_name = "software/glasgow/applet/video/scan_gen/1-3ML.bmp"

# with open(file_name, "rb") as f:
#     file_data = f.read()

# image_width = struct.unpack_from('<i', file_data, 18)[0]
# image_height = struct.unpack_from('<i', file_data, 22)[0]

# for i in range(10):
#     pixel = struct.unpack_from('<L', file_data, 54+i)
#     print(pixel)

def read_rows(path):
    image_file = open(path, "rb")
    # Blindly skip the BMP header.
    image_file.seek(54)

    # We need to read pixels in as rows to later swap the order
    # since BMP stores pixels starting at the bottom left.
    rows = []
    row = []
    pixel_index = 0

    while True:
        if pixel_index == 1920:
            pixel_index = 0
            rows.insert(0, row)
            if len(row) != 1920: #* 3:
                raise Exception("Row length is not 1920*3 but " + str(len(row)) + " / 3.0 = " + str(len(row) / 3.0))
            row = []
        pixel_index += 1

        r_string = image_file.read(1)
        #g_string = image_file.read(1)
        #b_string = image_file.read(1)

        if len(r_string) == 0:
            # This is expected to happen when we've read everything.
            if len(rows) != 1080:
                print("Warning!!! Read to the end of the file at the correct sub-pixel (red) but we've not read 1080 rows!")
            break

        # if len(g_string) == 0:
        #     print("Warning!!! Got 0 length string for green. Breaking.")
        #     break

        # if len(b_string) == 0:
        #     print("Warning!!! Got 0 length string for blue. Breaking.")
        #     break

        r = ord(r_string)
        # g = ord(g_string)
        # b = ord(b_string)

        # row.append(b)
        # row.append(g)
        row.append(r)

    image_file.close()

    return rows



rows = read_rows(file_name)

rows = np.array(rows)

# bitstream = str(list(np.ravel(rows)))
# with open("patternbytes.txt","w") as file:
#     file.write(bitstream)

# print(rows.shape)
# plt.imshow(rows)
# plt.show()

# This list is raw sub-pixel values. A red image is for example (255, 0, 0, 255, 0, 0, ...).

#print(sub_pixels)

pattern_img = Image.open(os.path.join(os.getcwd(), 'software/glasgow/applet/video/scan_gen/Nanographs Pattern Test Logo and Gradients.bmp'))
pattern_array = np.array(pattern_img)
pattern_array[0] = [1]*pattern_array.shape[0]
pattern_array[0][0] = 0
pattern_stream = np.ravel(pattern_array)
print(pattern_stream)


