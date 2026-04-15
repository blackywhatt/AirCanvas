class LessonEngine:

    def __init__(self, questions):
        self.questions = questions
        self.current_question = 0
        self.score = 0
        self.feedback = None
        self.feedback_timer = 0
        self.finish_timer = 0
        self.attempts = 0

    def get_current_question(self):
        if self.lesson_finished():
            return None
        return self.questions[self.current_question]

    def check_answer(self, answer):

        if self.lesson_finished():
            return

        correct = self.questions[self.current_question]["answer"]

        self.attempts += 1

        if answer == correct:
            self.feedback = "correct"

            if self.attempts == 1:
                self.score += 1
            elif self.attempts == 2:
                self.score += 0.5
            else:
                self.score += 0.2

            self.current_question += 1
            self.attempts = 0

        else:
            self.feedback = "wrong"

        self.feedback_timer = 30

    def update(self):

        if self.feedback_timer > 0:
            self.feedback_timer -= 1
        else:
            self.feedback = None

        if self.lesson_finished():
            self.finish_timer += 1

    def lesson_finished(self):
        return self.current_question >= len(self.questions)
    
    def get_progress(self):
        return self.current_question, len(self.questions)
    
    def should_exit(self):
        return self.finish_timer > 90   