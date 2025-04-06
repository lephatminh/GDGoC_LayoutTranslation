# GDGoC_LayoutTranslation

1. main.py => submission_part_1.csv, submission_part_2.csv, submission_part_3.csv, submission_part_4.csv

2. merge.py => submission.csv to merge all 4 parts into one and eliminate files that are not in sample_submission.csv. The original 2000 files are stored in submission_old.csv 

3. fill_missing_rows.py => submission_fill.csv to fill the rows with empty values in solution column by using ocrmypdf model

4. fix_format.py => submission_official.csv to adapt the submission format in Kaggle

ocr_my_pdf.py => submission_test.csv to test the efficiency of the ocrmypdf model
ocr_recovery.log => only for debugging purpose