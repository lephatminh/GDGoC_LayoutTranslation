import React, { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

const ViewPage: React.FC = () => {
  const navigate = useNavigate();

  const originalUrl = sessionStorage.getItem("originalUrl");
  const translatedUrl = sessionStorage.getItem("translatedUrl");

  const originalRef = useRef<HTMLDivElement>(null);
  const translatedRef = useRef<HTMLDivElement>(null);

  // Redirect to /upload if either file URL is missing
  useEffect(() => {
    if (!originalUrl || !translatedUrl) {
      navigate("/upload");
    }
  }, [navigate, originalUrl, translatedUrl]);

  // Scroll sync effect
  useEffect(() => {
    const left = originalRef.current;
    const right = translatedRef.current;

    if (!left || !right) return;

    let isSyncing = false;

    const syncScroll = (source: HTMLElement, target: HTMLElement) => {
      if (isSyncing) return;
      isSyncing = true;
      target.scrollTop = source.scrollTop;
      setTimeout(() => {
        isSyncing = false;
      }, 50);
    };

    const handleLeftScroll = () => syncScroll(left, right);
    const handleRightScroll = () => syncScroll(right, left);

    left.addEventListener("scroll", handleLeftScroll);
    right.addEventListener("scroll", handleRightScroll);

    return () => {
      left.removeEventListener("scroll", handleLeftScroll);
      right.removeEventListener("scroll", handleRightScroll);
    };
  }, []);

  if (!originalUrl || !translatedUrl) return null;

  return (
    <div className="d-flex flex-column vh-100 bg-dark text-light">
      <div className="d-flex flex-grow-1 overflow-hidden">
        {/* Original PDF */}
        <div
          ref={originalRef}
          className="w-50 h-100 overflow-auto border-end position-relative"
        >
          <div className="text-center fw-bold py-2 bg-light text-dark border-bottom sticky-top">
            Original
          </div>
          <iframe
            src={originalUrl}
            title="Original PDF"
            width="100%"
            height="100%"
            style={{ border: "none" }}
          />
        </div>

        {/* Translated PDF */}
        <div
          ref={translatedRef}
          className="w-50 h-100 overflow-auto position-relative"
        >
          <div className="text-center fw-bold py-2 bg-light text-dark border-bottom sticky-top">
            Translated
          </div>
          <iframe
            src={translatedUrl}
            title="Translated PDF"
            width="100%"
            height="100%"
            style={{ border: "none" }}
          />
        </div>
      </div>
    </div>
  );
};

export default ViewPage;
