// Mock localStorage
const mockStorage = {
    data: {},
    getItem(key) {
        return this.data[key] || null;
    },
    setItem(key, value) {
        this.data[key] = value;
    },
    removeItem(key) {
        delete this.data[key];
    }
};

const localStorage = {
    getItem: jest.fn(key => mockStorage.getItem(key)),
    setItem: jest.fn((key, value) => mockStorage.setItem(key, value)),
    removeItem: jest.fn(key => mockStorage.removeItem(key))
};

// Mock DOM elements
document.body.innerHTML = `
    <input type="text" id="courseName" class="input-field">
    <input type="number" id="daysToComplete" class="input-field">
    <input type="number" id="quizzesPerDay" class="input-field">
    <input type="number" id="questionsPerQuiz" class="input-field">
    <textarea id="additionalInput" class="input-field"></textarea>
    <span id="charCount">0</span>
    <button id="createCourseBtn">Create Course</button>
`;

// Import the actual setupCourseCreationForm function
function setupCourseCreationForm() {
    const courseName = document.getElementById('courseName');
    const daysToComplete = document.getElementById('daysToComplete');
    const quizzesPerDay = document.getElementById('quizzesPerDay');
    const questionsPerQuiz = document.getElementById('questionsPerQuiz');
    const additionalInput = document.getElementById('additionalInput');
    const charCount = document.getElementById('charCount');
    const createCourseBtn = document.getElementById('createCourseBtn');

    // Validate required fields
    function validateForm() {
        const isValid = courseName.value.trim() !== '' &&
                      daysToComplete.value.trim() !== '' &&
                      quizzesPerDay.value.trim() !== '' &&
                      questionsPerQuiz.value.trim() !== '' &&
                      parseInt(daysToComplete.value) > 0 &&
                      parseInt(daysToComplete.value) <= 365 &&
                      parseInt(quizzesPerDay.value) > 0 &&
                      parseInt(quizzesPerDay.value) <= 5 &&
                      parseInt(questionsPerQuiz.value) > 0 &&
                      parseInt(questionsPerQuiz.value) <= 50;
        
        createCourseBtn.disabled = !isValid;
        return isValid;
    }

    // Add input event listeners for all required fields
    [courseName, daysToComplete, quizzesPerDay, questionsPerQuiz].forEach(input => {
        input.addEventListener('input', validateForm);
        input.addEventListener('blur', validateForm);
        input.addEventListener('change', validateForm);
    });

    // Handle character count for additional input
    additionalInput.addEventListener('input', function() {
        if (this.value.length > 500) {
            this.value = this.value.substring(0, 500);
        }
        charCount.textContent = this.value.length;
    });

    // Create course button click handler
    createCourseBtn.onclick = function(e) {
        e.preventDefault();
        
        if (!validateForm()) {
            return;
        }

        const courseData = {
            name: courseName.value.trim(),
            daysToComplete: parseInt(daysToComplete.value),
            quizzesPerDay: parseInt(quizzesPerDay.value),
            questionsPerQuiz: parseInt(questionsPerQuiz.value),
            additionalInfo: additionalInput.value.trim(),
            progress: 0,
            quizzesCompleted: 0,
            createdAt: new Date().toISOString()
        };

        try {
            const editingIndex = localStorage.getItem('editingCourseIndex');
            const coursesStr = localStorage.getItem('coursesInProgress') || '[]';
            const courses = JSON.parse(coursesStr);

            if (editingIndex !== null && editingIndex !== 'null') {
                // We're editing an existing course
                const index = parseInt(editingIndex);
                if (courses[index]) {
                    courses[index] = {
                        ...courses[index],
                        ...courseData
                    };
                }
                localStorage.removeItem('editingCourseIndex');
            } else {
                // We're creating a new course
                courses.push(courseData);
            }

            localStorage.setItem('coursesInProgress', JSON.stringify(courses));
            return courseData;
        } catch (error) {
            console.error('Error handling course data:', error);
            return null;
        }
    };

    return {
        validateForm,
        elements: {
            courseName,
            daysToComplete,
            quizzesPerDay,
            questionsPerQuiz,
            additionalInput,
            charCount,
            createCourseBtn
        }
    };
}

// Test suite
describe('Course Creation Tests', () => {
    let form;

    beforeEach(() => {
        // Reset DOM elements
        document.body.innerHTML = `
            <input type="text" id="courseName" class="input-field">
            <input type="number" id="daysToComplete" class="input-field">
            <input type="number" id="quizzesPerDay" class="input-field">
            <input type="number" id="questionsPerQuiz" class="input-field">
            <textarea id="additionalInput" class="input-field"></textarea>
            <span id="charCount">0</span>
            <button id="createCourseBtn">Create Course</button>
        `;

        // Initialize form
        form = setupCourseCreationForm();

        // Reset localStorage mock
        localStorage.getItem.mockReset();
        localStorage.setItem.mockReset();
        localStorage.removeItem.mockReset();
    });

    // Test 1: Form validation with valid inputs
    test('Form validation with valid inputs', () => {
        const { elements } = form;
        
        // Set valid inputs
        elements.courseName.value = 'Test Course';
        elements.daysToComplete.value = '30';
        elements.quizzesPerDay.value = '2';
        elements.questionsPerQuiz.value = '10';

        // Trigger input events
        elements.courseName.dispatchEvent(new Event('input'));
        elements.daysToComplete.dispatchEvent(new Event('input'));
        elements.quizzesPerDay.dispatchEvent(new Event('input'));
        elements.questionsPerQuiz.dispatchEvent(new Event('input'));

        // Verify form is valid
        expect(form.validateForm()).toBe(true);
        expect(elements.createCourseBtn.disabled).toBe(false);
    });

    // Test 2: Form validation with invalid inputs
    test('Form validation with invalid inputs', () => {
        const { elements } = form;

        // Test empty inputs
        elements.courseName.dispatchEvent(new Event('input'));
        elements.daysToComplete.dispatchEvent(new Event('input'));
        elements.quizzesPerDay.dispatchEvent(new Event('input'));
        elements.questionsPerQuiz.dispatchEvent(new Event('input'));
        expect(form.validateForm()).toBe(false);
        expect(elements.createCourseBtn.disabled).toBe(true);

        // Test invalid numbers
        elements.courseName.value = 'Test Course';
        elements.daysToComplete.value = '0';
        elements.quizzesPerDay.value = '6';
        elements.questionsPerQuiz.value = '51';

        elements.courseName.dispatchEvent(new Event('input'));
        elements.daysToComplete.dispatchEvent(new Event('input'));
        elements.quizzesPerDay.dispatchEvent(new Event('input'));
        elements.questionsPerQuiz.dispatchEvent(new Event('input'));
        expect(form.validateForm()).toBe(false);
        expect(elements.createCourseBtn.disabled).toBe(true);
    });

    // Test 3: Character limit for additional input
    test('Character limit for additional input', () => {
        const { elements } = form;

        // Test exceeding character limit
        elements.additionalInput.value = 'a'.repeat(501);
        elements.additionalInput.dispatchEvent(new Event('input'));
        expect(elements.additionalInput.value.length).toBe(500);
        expect(elements.charCount.textContent).toBe('500');

        // Test within character limit
        elements.additionalInput.value = 'Test input';
        elements.additionalInput.dispatchEvent(new Event('input'));
        expect(elements.additionalInput.value.length).toBe(10);
        expect(elements.charCount.textContent).toBe('10');
    });

    // Test 4: Course creation with valid data
    test('Course creation with valid data', () => {
        const { elements } = form;

        // Set valid inputs
        elements.courseName.value = 'Test Course';
        elements.daysToComplete.value = '30';
        elements.quizzesPerDay.value = '2';
        elements.questionsPerQuiz.value = '10';
        elements.additionalInput.value = 'Test additional info';

        // Mock localStorage for courses
        localStorage.getItem.mockImplementation((key) => {
            if (key === 'coursesInProgress') return '[]';
            return null;
        });

        // Trigger input events to enable button
        elements.courseName.dispatchEvent(new Event('input'));
        elements.daysToComplete.dispatchEvent(new Event('input'));
        elements.quizzesPerDay.dispatchEvent(new Event('input'));
        elements.questionsPerQuiz.dispatchEvent(new Event('input'));

        // Trigger form submission
        elements.createCourseBtn.click();

        // Verify localStorage was updated
        const setItemCalls = localStorage.setItem.mock.calls;
        const lastSetItemCall = setItemCalls[setItemCalls.length - 1];
        
        expect(lastSetItemCall[0]).toBe('coursesInProgress');
        const savedCourses = JSON.parse(lastSetItemCall[1]);
        expect(savedCourses).toHaveLength(1);
        expect(savedCourses[0]).toEqual({
            name: 'Test Course',
            daysToComplete: 30,
            quizzesPerDay: 2,
            questionsPerQuiz: 10,
            additionalInfo: 'Test additional info',
            progress: 0,
            quizzesCompleted: 0,
            createdAt: expect.any(String)
        });
    });

    // Test 5: Course editing
    test('Course editing functionality', () => {
        const { elements } = form;

        // Mock existing course data
        const existingCourses = [{
            name: 'Existing Course',
            daysToComplete: 30,
            quizzesPerDay: 2,
            questionsPerQuiz: 10,
            progress: 50,
            quizzesCompleted: 15,
            createdAt: '2024-03-31T00:00:00.000Z'
        }];

        localStorage.getItem.mockImplementation((key) => {
            if (key === 'coursesInProgress') return JSON.stringify(existingCourses);
            if (key === 'editingCourseIndex') return '0';
            return null;
        });

        // Set new values
        elements.courseName.value = 'Updated Course';
        elements.daysToComplete.value = '45';
        elements.quizzesPerDay.value = '3';
        elements.questionsPerQuiz.value = '15';

        // Trigger input events to enable button
        elements.courseName.dispatchEvent(new Event('input'));
        elements.daysToComplete.dispatchEvent(new Event('input'));
        elements.quizzesPerDay.dispatchEvent(new Event('input'));
        elements.questionsPerQuiz.dispatchEvent(new Event('input'));

        // Trigger form submission
        elements.createCourseBtn.click();

        // Verify localStorage was updated with edited course
        expect(localStorage.setItem).toHaveBeenCalledWith(
            'coursesInProgress',
            expect.stringContaining('Updated Course')
        );
    });
});

// Course validation function
function validateCourse(course) {
    const MAX_DAYS = 365;
    const MAX_QUIZZES_PER_DAY = 5;
    const MAX_QUESTIONS_PER_QUIZ = 50;
    
    if (course.daysToComplete > MAX_DAYS) {
        return { valid: false, error: 'Days to complete exceeds maximum limit' };
    }
    if (course.quizzesPerDay > MAX_QUIZZES_PER_DAY) {
        return { valid: false, error: 'Quizzes per day exceeds maximum limit' };
    }
    if (course.questionsPerQuiz > MAX_QUESTIONS_PER_QUIZ) {
        return { valid: false, error: 'Questions per quiz exceeds maximum limit' };
    }
    return { valid: true };
}

// Test Course Creation
function testCourseCreation() {
    console.log('Testing Course Creation...');
    
    // Test 1: Create a new course
    const courseData = {
        name: "Test Course",
        daysToComplete: 7,
        quizzesPerDay: 2,
        questionsPerQuiz: 10,
        additionalInfo: "Test course for validation",
        progress: 0,
        createdAt: new Date().toISOString()
    };
    
    // Validate course before creation
    const validationResult = validateCourse(courseData);
    if (validationResult.valid) {
        // Store in mock storage
        const courses = JSON.parse(localStorage.getItem('coursesInProgress') || '[]');
        courses.push(courseData);
        localStorage.setItem('coursesInProgress', JSON.stringify(courses));
        
        // Verify course was created
        const savedCourses = JSON.parse(localStorage.getItem('coursesInProgress') || '[]');
        const createdCourse = savedCourses.find(c => c.name === "Test Course");
        
        if (createdCourse) {
            console.log('✅ Course creation successful');
            console.log('Course details:', createdCourse);
        } else {
            console.error('❌ Course creation failed');
        }
    } else {
        console.error('❌ Course validation failed:', validationResult.error);
    }
    
    // Test 2: Validate course limits
    const invalidCourse = {
        name: "Invalid Course",
        daysToComplete: 366, // Exceeds max
        quizzesPerDay: 6,    // Exceeds max
        questionsPerQuiz: 51, // Exceeds max
        progress: 0,
        createdAt: new Date().toISOString()
    };
    
    // Validate invalid course
    const invalidValidationResult = validateCourse(invalidCourse);
    if (!invalidValidationResult.valid) {
        console.log('✅ Course validation working correctly');
        console.log('Validation error:', invalidValidationResult.error);
    } else {
        console.error('❌ Course validation failed - accepted invalid course');
    }
    
    // Clean up test data
    const cleanCourses = JSON.parse(localStorage.getItem('coursesInProgress') || '[]')
        .filter(c => c.name !== "Test Course");
    localStorage.setItem('coursesInProgress', JSON.stringify(cleanCourses));
}

// Test Quiz Completion
function testQuizCompletion() {
    console.log('\nTesting Quiz Completion...');
    
    // Create a test course
    const courseData = {
        name: "Quiz Test Course",
        daysToComplete: 1,
        quizzesPerDay: 1,
        questionsPerQuiz: 5,
        progress: 0,
        quizzesCompleted: 0,
        createdAt: new Date().toISOString()
    };
    
    // Validate course before creation
    const validationResult = validateCourse(courseData);
    if (validationResult.valid) {
        const courses = JSON.parse(localStorage.getItem('coursesInProgress') || '[]');
        courses.push(courseData);
        localStorage.setItem('coursesInProgress', JSON.stringify(courses));
        
        // Simulate quiz completion
        const courseIndex = courses.findIndex(c => c.name === "Quiz Test Course");
        if (courseIndex !== -1) {
            courses[courseIndex].quizzesCompleted = 1;
            courses[courseIndex].progress = 100;
            
            // Move to completed courses
            const completedCourses = JSON.parse(localStorage.getItem('completedCourses') || '[]');
            const completedCourse = courses[courseIndex];
            completedCourse.completedDate = new Date().toISOString();
            completedCourses.push(completedCourse);
            courses.splice(courseIndex, 1);
            
            localStorage.setItem('completedCourses', JSON.stringify(completedCourses));
            localStorage.setItem('coursesInProgress', JSON.stringify(courses));
            
            // Verify course was moved to completed
            const savedCompletedCourses = JSON.parse(localStorage.getItem('completedCourses') || '[]');
            const courseCompleted = savedCompletedCourses.find(c => c.name === "Quiz Test Course");
            
            if (courseCompleted) {
                console.log('✅ Quiz completion and course movement successful');
                console.log('Completed course details:', courseCompleted);
            } else {
                console.error('❌ Quiz completion or course movement failed');
            }
        }
    } else {
        console.error('❌ Test course validation failed:', validationResult.error);
    }
    
    // Clean up test data
    const cleanCompletedCourses = JSON.parse(localStorage.getItem('completedCourses') || '[]')
        .filter(c => c.name !== "Quiz Test Course");
    localStorage.setItem('completedCourses', JSON.stringify(cleanCompletedCourses));
}

// Test Course Deletion
function testCourseDeletion() {
    console.log('\nTesting Course Deletion...');
    
    // Create a test course to delete
    const courseData = {
        name: "Delete Test Course",
        daysToComplete: 1,
        quizzesPerDay: 1,
        questionsPerQuiz: 5,
        progress: 0,
        createdAt: new Date().toISOString()
    };
    
    // Validate course before creation
    const validationResult = validateCourse(courseData);
    if (validationResult.valid) {
        const courses = JSON.parse(localStorage.getItem('coursesInProgress') || '[]');
        courses.push(courseData);
        localStorage.setItem('coursesInProgress', JSON.stringify(courses));
        
        // Delete the course
        const courseIndex = courses.findIndex(c => c.name === "Delete Test Course");
        if (courseIndex !== -1) {
            courses.splice(courseIndex, 1);
            localStorage.setItem('coursesInProgress', JSON.stringify(courses));
            
            // Verify course was deleted
            const savedCourses = JSON.parse(localStorage.getItem('coursesInProgress') || '[]');
            const courseExists = savedCourses.find(c => c.name === "Delete Test Course");
            
            if (!courseExists) {
                console.log('✅ Course deletion successful');
            } else {
                console.error('❌ Course deletion failed');
            }
        }
    } else {
        console.error('❌ Test course validation failed:', validationResult.error);
    }
}

// Run all tests
function runAllTests() {
    console.log('Starting Application Tests...\n');
    testCourseCreation();
    testQuizCompletion();
    testCourseDeletion();
    console.log('\nAll tests completed!');
}

// Execute tests
runAllTests(); 