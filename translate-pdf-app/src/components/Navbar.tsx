import React from "react";
import { Link, useLocation } from "react-router-dom";
import { FaFilePdf } from "react-icons/fa";

const Navbar: React.FC = () => {
  const location = useLocation();

  return (
    <nav className="navbar navbar-expand-lg navbar-dark bg-dark px-4">
      <Link to="/" className="navbar-brand d-flex align-items-center">
        <FaFilePdf className="me-2 text-danger" size={24} />
        <span className="fw-bold text-white">VerbaDoc</span>
      </Link>

      <div className="ms-auto d-flex gap-3">
        <Link
          to="/"
          className={`btn btn-outline-light ${
            location.pathname === "/" ? "active" : ""
          }`}
        >
          Home
        </Link>
        <Link
          to="/upload"
          className={`btn btn-outline-light ${
            location.pathname === "/upload" ? "active" : ""
          }`}
        >
          Upload
        </Link>
      </div>
    </nav>
  );
};

export default Navbar;
