# Notice

As the model size is large to upload to github, please download the ```best.pt``` model in the ```model.txt``` link.

# Repo Structure

- ```best.pt```: YOLO model used to detect the Math Equation in a given PDF
- ```detection.ipynb```: Run script
- ```visualization.ipynb```: Visualize the croped math equation image to the give pdf
- ```README.markdown```: instruction
- Stuff of PDF and a sample output Folder (```Super_Math_notaion```)

# How to use

- First, you put your pdf in this folder (same folder with ```detection.ipynb```)

- In the ```detection.ipynb```, you pass the name of the pdf at the ```name_root``` variable (e.g ```name_root = 'Super_Math_notation'```)

- Then, you run all the cell in the ```detection.ipynb```

# Pipeline of Detection Process (```detection.ipynb```)

 Assume that the pdf file is ```Super_Math_notation.pdf```. The below is the process:

   **1.** Create a folder with same name as the pdf (e.g ```./Super_Math_notation```)

   **2.** Convert the pdf (e.g ```Super_Math_notation.pdf```) to jpg (e.g ```Super_Math_notation.jpg```) with the same name

   **3.** Put the jpg file to the folder (e.g ```./Super_Math_notation/Super_Math_notation.jpg```) and also adding one more file call ```size.txt``` (include size of the jpg and size of the pdf - the first tuple is the image size the second tuple is the pdf size, e.g ```./Super_Math_notation/size.txt```)

   **4.** Then the YOLO model will perform the Math Equation detection, result in the ```.txt``` with the same name of the pdf (e.g ```./Super_Math_notation/Super_Math_notation.txt```). This txt file include many line, each line will look like:
    
    ```0.9036 1972.1656 2192.7507 2242.2212 2261.0522```

   The fist numebr is the confidence of the box for the detecting region as a math equation.

   The four number is the (x1,y1) and (x2,y2) with respective to top left and bottom right corner of the box. In this case, that is (1972.1656, 2192.7507) and (2242.2212 , 2261.0522) respectively.

   **5.** We then make copy of the above .txt file, replace the confidence number of each line to it index (or order). Regarding the above line, assume it is the first line in the ```Super_Math_notation.txt```:
    
   Orginal:
    
    ```0.9036 1972.1656 2192.7507 2242.2212 2261.0522``` 
    
   Replace:
    
    ```1 1972.1656 2192.7507 2242.2212 2261.0522```

   Then, we save this file with name ```index.txt``` (e.g ```./Super_Math_notation/index.txt```)

   **6.** Then, we go to the ```index.txt``` (e.g ```./Super_Math_notation/index.txt```), get the box in this file (top left point and bottom right point), cut the image of the box correspondingly in  the jpg file (e.g ```./Super_Math_notation/Super_Math_notation.jpg```). We name each crop image with its respective index in the ```index.txt``` (e.g 1.jpg, 2.jpg,...) then store these file in a new folder called ```images```. Sample paths:
    
   ```./Super_Math_notation/images/1.jpg```

   ```./Super_Math_notation/images/2.jpg```

   **7.** Finally, we convert the coordinate in the ```index.txt``` (which currently in jpg scale) back to the PDF scale by getting the coordinate in the .txt come up with the jpg, PDF size ffrom the ```size.txt```. The resulted coordinate is save in the ```pdf_coor.txt```

# Output

After running the ```detection.ipynb``` script, you will see a folder with the same name with the input pdf. In this case, you will have:

```
YOLO_Math_detection
├── Super_Math_notation
│   ├── images
│   │   ├── 1.jpg
│   │   ├── 2.jpg
│   │   ├── ...
│   ├── index.txt
│   ├── pdf_coor.txt
│   ├── size.txt
│   ├── Super_Math_notation.jpg
│   └── Super_Math_notation.txt
├── best.pt
├── README
├── detection.ipynb
├── Super_Math_notation.pdf
└── visualization.ipynb
```

# Pipeline of Visualization process (```visualization.ipynb```)

Before going to the process of visualization, the purpose of this repo initially for getting the math equation in a given PDF as a image format and re-display on the original PDF.

 1. Given the PDF, this script require the ```<PDF name> folder``` which contain ```index.txt```, ```size.txt```, and cropped images folder (```images```).

 2. Then the script will check if the size of the input PDF match the size in the ```size.txt``` in the ```<PDF name> folder```

    - If yes, it perform the insert process

    - If no, it resize the PDF and save as new PDF with prefix ```_scale.pdf``` and perform insertion on this PDF.

 2. Then, it will check for a ```pdf_coor.txt``` in the ```<PDF name> folder```, if the ```pdf_coor.txt``` not found, it will raise an error. Otherwise, it will use coordinate in the ```pdf_coor.txt``` and respective image in the ```images``` folder, plot it to a given PDF.

 3. After all the image are plot, it save the new PDF with prefix ```_insert_images.pdf```

# Result after Detect and Visualize

|Sample|Math Equation detected in the Sample|
|-|-|
|***Sample 1***![Alt text](imgs/sample_1.jpg)|![Alt text](imgs/sample_1_result.jpg)|
|***Sample 2***![Alt text](imgs/sample_2.jpg)|![Alt text](imgs/sample_2_result.jpg)|