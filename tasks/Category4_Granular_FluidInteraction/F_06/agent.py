import math



def build_agent(sandbox):

                                                         

    beams = []

          

    for i in range(3):

        x = 6.5 + i * 1.0

        y = 0.5 + i * 0.7

        b = sandbox.add_beam(x, y, 1.1, 0.2, angle=0.6, density=50.0)

        sandbox.add_joint(b, None, (x, 0.0), type='rigid')

        beams.append(b)

                 

    for i in range(9):

        x = 9.5 + i * 1.0

        y = 2.5

        b = sandbox.add_beam(x, y, 1.1, 0.2, angle=0, density=50.0)

        sandbox.add_joint(b, None, (x, 0.0), type='rigid')

        beams.append(b)

    return beams[0]



def agent_action(sandbox, agent_body, step_count):

    if not hasattr(sandbox, "get_fluid_particles") or not hasattr(sandbox, "apply_force_to_particle"):

        return

    

    budget = getattr(sandbox, 'FORCE_BUDGET_PER_STEP', 12000.0)

    particles = sandbox.get_fluid_particles()

    if not particles:

        return

    

               

                                              

                                   

                                     

    

    def get_prio(p):

        px = p.position.x

        if 10.0 <= px <= 18.0: return 0

        if px < 10.0: return 1

        return 2

        

    particles.sort(key=get_prio)

    

    used = 0.0

    m = 25.0

    g = 10.0

    

    for p in particles:

        if used >= budget:

            break

        

        x, y = p.position.x, p.position.y

        vx, vy = p.linearVelocity.x, p.linearVelocity.y

        

        fx, fy = 0.0, 0.0

        

        if x > 22.0:

                                        

            fx = -m * 10.0 * (vx + 2.0)

            fy = m * g

        elif x >= 18.0:

                                           

            if abs(vx) > 0.2:

                fx = -m * 10.0 * vx

            if y > 0.2:

                fy = -m * 5.0

        elif x < 6.0:

                                 

            target_vx = 5.0

            target_vy = 2.0

            fx = m * 5.0 * (target_vx - vx)

            fy = m * (g + 5.0 * (target_vy - vy))

        else:

                         

            target_vx = 6.0

            target_vy = 0.0

            if y < 2.6:

                target_vy = 3.0                      

            

            fx = m * 5.0 * (target_vx - vx)

            fy = m * (g + 5.0 * (target_vy - vy))

            

            if y > 3.0:

                fx += 150.0            

                

        mag = math.sqrt(fx*fx + fy*fy)

        if mag > 0:

            if used + mag <= budget:

                sandbox.apply_force_to_particle(p, fx, fy)

                used += mag

            else:

                scale = (budget - used) / mag

                if scale > 0.1:

                    sandbox.apply_force_to_particle(p, fx * scale, fy * scale)

                    used = budget

