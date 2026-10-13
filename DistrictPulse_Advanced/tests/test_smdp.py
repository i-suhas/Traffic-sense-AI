from districtpulse.smdp import SMDPQLearner, Transition

def test_duration_discount_update_changes_q_value():
    agent=SMDPQLearner(actions=(10,15),alpha=1.0,gamma=0.5,epsilon=0.0,seed=1)
    agent.update(Transition((0,),0,2,-4.0,(1,)))
    assert agent.values((0,))[0] == -4.0

def test_state_action_dimensions():
    agent=SMDPQLearner(actions=(10,15,20))
    assert len(agent.values((1,2))) == 3
