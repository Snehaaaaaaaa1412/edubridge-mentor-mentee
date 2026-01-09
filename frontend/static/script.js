const departmentInterests = {
    "Computer Science and Engineering": [
        "Data Mining", "Data Warehousing", "Big Data", "Machine Learning",
        "Cloud Computing", "Cyber Security", "Blockchain", "Computer Vision",
        "Pattern Recognition", "Graph Theory", "IoT", "Edge Computing", 
        "Wireless Sensor Networks", "Health Informatics"
    ],
    "Electronics and Communication Engineering": [
        "Optical Communication Systems", "Radio-over-Fiber", "Soliton Transmission",
        "Broadband Optical Networks", "Dispersion Compensation"
    ],
    "Applied Sciences": [
        "Computational Fluid Dynamics", "Numerical Analysis"
    ]
};

function toggleFields() {
    const role = document.getElementById("role").value;
    const mentorFields = document.getElementById("mentor-fields");
    const menteeFields = document.getElementById("mentee-fields");

    if (role === "mentor") {
        mentorFields.style.display = "block";
        menteeFields.style.display = "none";
    } else {
        mentorFields.style.display = "none";
        menteeFields.style.display = "block";
    }
}

function updateInterests() {
    const department = document.getElementById("department").value;
    const interestsSelect = document.getElementById("interests");

    // Clear old options
    interestsSelect.innerHTML = "";

    if (departmentInterests[department]) {
        departmentInterests[department].forEach(interest => {
            const option = document.createElement("option");
            option.value = interest;
            option.textContent = interest;
            interestsSelect.appendChild(option);
        });
    }
}

window.onload = function () {
    toggleFields();
    updateInterests();
};
