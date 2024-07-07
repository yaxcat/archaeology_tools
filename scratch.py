

def cantor_pairing(oid1, oid2):
    if oid1 == oid2:
        #arcpy.AddWarning("Two or more points have the same ID.  Point IDs must be unique to use this tool.")
        return
    # Make sure the pairwise function always consumes the IDs in the same order so that return value is
    # consistent.  For example (3,5) and (5,3) should both return 41.
    if oid1 < oid2:
        k1 = oid1
        k2 = oid2
    else:
        k1 = oid2
        k2 = oid1
    pair_id = (k1 + k2) * (k1 + k2 + 1)/2 + k2
    return int(pair_id)


a = cantor_pairing(3,5)
b = cantor_pairing(5, 3)

print(a)
print(b)

my_set = set()

my_set.add(1)
my_set.add(2)

print(my_set)

if 1 in my_set:
    print('True')
else:
    print('False')