using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using Newtonsoft.Json;
using UglyToad.PdfPig;
using UglyToad.PdfPig.Content;  // Add this
using UglyToad.PdfPig.DocumentLayoutAnalysis;
using UglyToad.PdfPig.DocumentLayoutAnalysis.PageSegmenter;
using UglyToad.PdfPig.DocumentLayoutAnalysis.ReadingOrderDetector;
using UglyToad.PdfPig.DocumentLayoutAnalysis.WordExtractor;
using UglyToad.PdfPig.Geometry;  // Add this

namespace PDFPigLayoutDetection
{
    class Program
    {
        static void Main(string[] args)
        {
            // File paths. Update the path to go up one directory level
            string pdfDir = Path.Combine("..", "data", "test", "testing");
            string outputCsv = "submission_pdfpig.csv";

            // Ensure directories exist
            Directory.CreateDirectory(pdfDir);

            // Process PDFs
            ProcessPdfsWithPdfPig(pdfDir, outputCsv);
        }

        /// <summary>
        /// Process all PDFs in a directory using PDFPig and save results to CSV
        /// </summary>
        /// <param name="pdfDir">Directory containing PDF files</param>
        /// <param name="outputCsv">Path to output CSV file</param>
        static void ProcessPdfsWithPdfPig(string pdfDir, string outputCsv)
        {
            // Get all PDF files
            var pdfFiles = Directory.GetFiles(pdfDir, "*.pdf");
            int totalFiles = pdfFiles.Length;

            // Create CSV file with header
            using (var writer = new StreamWriter(outputCsv, false, Encoding.UTF8))
            {
                writer.WriteLine("id,solution");
            }

            // Process each PDF
            for (int idx = 0; idx < totalFiles; idx++)
            {
                string pdfFile = pdfFiles[idx];
                string fileId = Path.GetFileNameWithoutExtension(pdfFile);

                // Clean up fileId by removing .coco_standard suffix if present
                if (fileId.EndsWith(".coco_standard"))
                {
                    fileId = fileId.Replace(".coco_standard", "");
                }

                Console.WriteLine($"[{idx + 1}/{totalFiles}] Processing: {fileId}");

                try
                {
                    // Extract layout information
                    var cells = ExtractPdfLayout(pdfFile);

                    // Skip if no cells were found
                    if (cells.Count == 0)
                    {
                        Console.WriteLine($"No cells extracted from {fileId}, skipping");
                        continue;
                    }

                    // Save to CSV
                    using (var writer = new StreamWriter(outputCsv, true, Encoding.UTF8))
                    {
                        string jsonStr = JsonConvert.SerializeObject(cells);
                        writer.WriteLine($"{fileId},{jsonStr}");
                    }

                    Console.WriteLine($"Saved result for {fileId} with {cells.Count} blocks");
                }
                catch (Exception ex)
                {
                    Console.Error.WriteLine($"Error processing {fileId}: {ex.Message}");
                }
            }

            Console.WriteLine($"Processing complete! {totalFiles} files processed.");
        }

        /// <summary>
        /// Extract text with layout information from a PDF using PDFPig,
        /// which can identify paragraphs rather than just individual lines.
        /// </summary>
        /// <param name="pdfPath">Path to the PDF file</param>
        /// <returns>List of cell dictionaries containing text and positioning information</returns>
        static List<CellInfo> ExtractPdfLayout(string pdfPath)
        {
            var cells = new List<CellInfo>();

            try
            {
                // Open the PDF document
                using (var document = PdfDocument.Open(pdfPath))
                {
                    // Process each page
                    for (int pageNum = 0; pageNum < document.NumberOfPages; pageNum++)
                    {
                        try
                        {
                            // Get the page (1-based index)
                            var page = document.GetPage(pageNum + 1);
                            Console.WriteLine($"Processing page {pageNum + 1} of {document.NumberOfPages}");

                            // Extract words using nearest neighbor algorithm
                            var wordExtractor = NearestNeighbourWordExtractor.Instance;
                            var words = wordExtractor.GetWords(page.Letters);

                            // Use page segmenter to identify paragraphs and text blocks
                            IEnumerable<TextBlock> textBlocks = null;
                            try
                            {
                                // Try DocstrumBoundingBoxes implementation
                                var docstrum = DocstrumBoundingBoxes.Instance;
                                textBlocks = docstrum.GetBlocks(words);
                            }
                            catch (Exception docstrumErr)
                            {
                                Console.Error.WriteLine($"DocstrumBoundingBoxes failed: {docstrumErr.Message}");

                                // Fallback: Create one text block per line
                                var lineBlocks = new List<TextBlock>();

                                // Group words by approximate line (y-coordinate)
                                var wordsByLine = words
                                    .GroupBy(w => (float)(Math.Round(w.BoundingBox.Bottom / 5) * 5))
                                    .OrderByDescending(g => g.Key);

                                foreach (var lineGroup in wordsByLine)
                                {
                                    // Order words left to right within each line
                                    var lineWords = lineGroup.OrderBy(w => w.BoundingBox.Left).ToList();
                                    if (lineWords.Count > 0)
                                    {
                                        var textLine = new TextLine(lineWords);
                                        lineBlocks.Add(new TextBlock(new List<TextLine> { textLine }));
                                    }
                                }

                                textBlocks = lineBlocks;
                            }

                            // Try to apply reading order
                            IEnumerable<TextBlock> orderedBlocks = null;
                            try
                            {
                                // Use UnsupervisedReadingOrderDetector
                                var readingOrder = UnsupervisedReadingOrderDetector.Instance;
                                orderedBlocks = readingOrder.Get(textBlocks.ToList());
                            }
                            catch (Exception orderErr)
                            {
                                Console.Error.WriteLine($"ReadingOrderDetector failed: {orderErr.Message}");
                                // If reading order fails, just use the blocks as-is
                                orderedBlocks = textBlocks;
                            }

                            // Process each text block
                            int blockIdx = 0;
                            foreach (var block in orderedBlocks)
                            {
                                try
                                {
                                    // Extract text from the block
                                    string blockText = block.Text;

                                    // Skip empty blocks
                                    if (string.IsNullOrWhiteSpace(blockText))
                                    {
                                        continue;
                                    }

                                    // Get bounding box coordinates
                                    var bounds = block.BoundingBox;
                                    float x = (float)bounds.Left;
                                    float y = (float)bounds.Bottom;
                                    float width = (float)bounds.Width;
                                    float height = (float)bounds.Height;


                                    // Create cell information
                                    var cell = new CellInfo
                                    {
                                        X = x,
                                        Y = y,
                                        Width = width,
                                        Height = height,
                                        Text = blockText.Trim(),
                                        BlockType = "paragraph",
                                        Page = pageNum + 1,
                                        BlockIndex = blockIdx
                                    };

                                    cells.Add(cell);
                                    blockIdx++;
                                }
                                catch (Exception blockErr)
                                {
                                    Console.Error.WriteLine($"Error processing block {blockIdx}: {blockErr.Message}");
                                }
                            }
                        }
                        catch (Exception pageErr)
                        {
                            Console.Error.WriteLine($"Error processing page {pageNum + 1}: {pageErr.Message}");
                            continue;
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"Error processing PDF {pdfPath}: {ex.Message}");
            }

            return cells;
        }
    }

    /// <summary>
    /// Represents information about a text block/cell in the PDF
    /// </summary>
    class CellInfo
    {
        // Basic positioning and text properties
        public float X { get; set; }
        public float Y { get; set; }
        public float Width { get; set; }
        public float Height { get; set; }
        public string Text { get; set; }
        public string BlockType { get; set; }
        public int Page { get; set; }
        public int BlockIndex { get; set; }

        // Font information (optional)
        // public FontInfo Font { get; set; }
    }

    /// <summary>
    /// Represents font information for a text block
    /// </summary>
    // class FontInfo
    // {
    //     public string Name { get; set; }
    //     public float Size { get; set; }
    //     public List<int> Color { get; set; }
    // }
}