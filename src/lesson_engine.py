class LessonEngine:

    def __init__(self, questions):
        self.questions = questions
        self.current_question = 0
        self.score = 0
        self.feedback = None
        self.feedback_timer = 0

    def get_current_question(self):
        return self.questions[self.current_question]

    def check_answer(self, answer):
        correct = self.questions[self.current_question]["answer"]
        if answer == correct:
            self.feedback = "correct"
            self.score += 1
            self.current_question += 1
        else:
            self.feedback = "wrong"

        self.feedback_timer = 30   # show feedback for some frames

    def update(self):

        if self.feedback_timer > 0:
            self.feedback_timer -= 1
        else:
            self.feedback = None

    def lesson_finished(self):
        return self.current_question >= len(self.questions)