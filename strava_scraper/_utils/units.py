import time

class Unit(object):
    def __init__(self, value):
        self.value = value

    def for_human(self):
        return ''

UNIT_EMPTY = Unit(None)

class Distance(Unit):
    def for_human(self):
        if not self.value:
            return ''
        if self.value < 2000:
            return '%.0f m' % self.m()
        return '%.2f km' % self.km()

    def m(self):
        return self.value

    def km(self):
        return self.value / 1000


class Elevation(Distance):
    def for_human(self):
        if not self.value:
            return ''
        return '%d m' % self.m()

class Duration(Unit):
    def for_human(self):
        if not self.value:
            return ''
        if self.value < 60:
            value = time.strftime("%Ss", time.gmtime(self.value))
        elif self.value < 60*60:
            value = time.strftime("%Mm %Ss", time.gmtime(self.value))
        else:
            value = time.strftime("%Hh %Mm", time.gmtime(self.value))
        return value[1:] if value[0] == '0' else value

    def hours(self):
        return self.value / (60.0 * 60.0)

    def minutes(self):
        return self.value / 60.0

    def seconds(self):
        return self.value

class Speed(Unit):
    def __init__(self, duration, distance, unit):
        if UNIT_EMPTY not in (duration, distance):
            self.value = distance.m() / duration.seconds()
        else:
            self.value = None
        self.unit = unit

    def kmh(self):
        return self.value * 3.6

    def ms(self):
        return self.value

    def for_human(self):
        if not self.value:
            return ''

        formula = getattr(self, self.unit)
        return '%.1f %s' % (formula(), self.unit)

class Pace(Unit):
    def __init__(self, duration, distance, unit):
        if UNIT_EMPTY not in (duration, distance):
            self.value = duration.minutes() / distance.km()
        else:
            self.value = None
        self.unit = unit

    def minkm(self):
        return self.value

    def min100m(self):
        return self.value / 10

    def for_human(self):
        if not self.value:
            return ''

        formula = getattr(self, self.unit)
        value = time.strftime("%M'%S", time.gmtime(formula()*60))
        return value[1:] if value[0] == '0' else value
