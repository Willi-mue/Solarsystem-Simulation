from logic import Planet

sun = Planet(0, 0, 30, (255, 204, 0), 1.98892 * 10 ** 30) 
sun.light = True

mercury = Planet(0.387 * Planet.AU, 0, 8, (169, 169, 169), 3.30 * 10 ** 23) 
mercury.y_vel = -47.4 * 1000

venus = Planet(0.723 * Planet.AU, 0, 14, (218, 165, 32), 4.8685 * 10 ** 24)  
venus.y_vel = -35.02 * 1000

earth = Planet(-1 * Planet.AU, 0, 16, (0, 102, 204), 5.9742 * 10 ** 24) 
earth.y_vel = 29.783 * 1000

mars = Planet(-1.524 * Planet.AU, 0, 12, (188, 39, 50), 6.39 * 10 ** 23)  
mars.y_vel = 24.077 * 1000

jupiter = Planet(5.203 * Planet.AU, 0, 25, (210, 180, 140), 1.898 * 10 ** 27) 
jupiter.y_vel = -13.07 * 1000

saturn = Planet(9.537 * Planet.AU, 0, 23, (222, 184, 135), 5.683 * 10 ** 26)  
saturn.y_vel = -9.69 * 1000

uranus = Planet(19.191 * Planet.AU, 0, 20, (173, 216, 230), 8.681 * 10 ** 25)  
uranus.y_vel = -6.81 * 1000

neptune = Planet(30.07 * Planet.AU, 0, 20, (0, 0, 128), 1.024 * 10 ** 26) 
neptune.y_vel = -5.43 * 1000

pluto = Planet(39.5 * Planet.AU, 0, 6, (200, 200, 200), 1.309 * 10 ** 22)
pluto.y_vel = -4.74 * 1000

solar_system = [sun, mercury, venus, earth, mars, jupiter, saturn, uranus, neptune, pluto]
